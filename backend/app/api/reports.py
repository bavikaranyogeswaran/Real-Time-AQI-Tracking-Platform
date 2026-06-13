import asyncio
import io
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.alert import Alert
from app.models.location import Location
from app.rate_limit import limiter
from app.services.analytics import get_aqi_distribution, get_daily_averages, get_forecast_accuracy

router = APIRouter()


async def _get_location(session: AsyncSession, city: str) -> Location:
    result = await session.execute(select(Location).where(Location.city.ilike(city)))
    location = result.scalars().first()
    if not location:
        raise HTTPException(status_code=404, detail=f"City '{city}' not found")
    return location


def _build_pdf(
    city: str,
    days: int,
    daily_avgs: list[dict],
    distribution: list[dict],
    accuracy: dict,
    active_alerts: int,
) -> bytes:
    """Build the PDF synchronously (called via asyncio.to_thread)."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        HRFlowable,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    normal = styles["Normal"]
    small = styles["Normal"].clone("small")
    small.fontSize = 8
    small.textColor = colors.HexColor("#6b7280")

    header_color = colors.HexColor("#e5e7eb")
    alt_row_color = colors.HexColor("#f9fafb")
    border_color = colors.HexColor("#d1d5db")

    def _table_style(n_data_rows: int) -> TableStyle:
        cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), header_color),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, border_color),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, alt_row_color]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]
        return TableStyle(cmds)

    story = []

    # Title & subtitle
    story.append(Paragraph(f"Air Quality Report — {city}", title_style))
    story.append(
        Paragraph(
            f"Generated {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')} · Last {days} days",
            small,
        )
    )
    story.append(Spacer(1, 16))

    # Daily averages table
    story.append(Paragraph("7-Day Daily Averages", styles["h2"]))
    story.append(Spacer(1, 6))
    if daily_avgs:
        avg_rows = [["Date", "Avg AQI", "Min AQI", "Max AQI"]]
        for row in daily_avgs:
            avg_rows.append([
                str(row["date"]),
                str(round(row["avg_aqi"], 1)),
                str(row["min_aqi"]),
                str(row["max_aqi"]),
            ])
        avg_table = Table(avg_rows, colWidths=[4 * cm, 3 * cm, 3 * cm, 3 * cm])
        avg_table.setStyle(_table_style(len(daily_avgs)))
        story.append(avg_table)
    else:
        story.append(Paragraph("No daily data available for this period.", normal))

    story.append(Spacer(1, 16))

    # AQI distribution table
    story.append(Paragraph("AQI Distribution", styles["h2"]))
    story.append(Spacer(1, 6))
    if distribution:
        total_count = sum(r["count"] for r in distribution)
        dist_rows = [["Category", "Count", "%"]]
        for row in distribution:
            pct = f"{row['count'] / total_count * 100:.1f}%" if total_count else "—"
            dist_rows.append([row["category"], str(row["count"]), pct])
        dist_table = Table(dist_rows, colWidths=[8 * cm, 3 * cm, 2 * cm])
        dist_table.setStyle(_table_style(len(distribution)))
        story.append(dist_table)
    else:
        story.append(Paragraph("No distribution data available.", normal))

    story.append(Spacer(1, 16))

    # Forecast accuracy
    story.append(Paragraph("Forecast Accuracy", styles["h2"]))
    story.append(Spacer(1, 6))
    if accuracy.get("sample_count", 0) > 0:
        story.append(Paragraph(f"MAE: {accuracy['mae']} AQI points", normal))
        story.append(Paragraph(f"RMSE: {accuracy['rmse']} AQI points", normal))
        story.append(Paragraph(f"Based on {accuracy['sample_count']} matched predictions", small))
    else:
        story.append(Paragraph("No forecast accuracy data available for this period.", normal))

    story.append(Spacer(1, 16))

    # Active alerts
    story.append(Paragraph("Active Alerts", styles["h2"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"Currently active alerts: {active_alerts}", normal))

    story.append(Spacer(1, 24))
    story.append(HRFlowable(width="100%", thickness=0.5, color=border_color))
    story.append(Spacer(1, 6))
    footer = styles["Normal"].clone("footer")
    footer.fontSize = 8
    footer.textColor = colors.HexColor("#9ca3af")
    footer.alignment = 2  # right
    story.append(Paragraph("AQI Tracker Platform · Data sourced from OpenWeather &amp; OpenAQ", footer))

    doc.build(story)
    return buf.getvalue()


@router.get("/reports/city-pdf")
@limiter.limit("5/minute")
async def city_pdf_report(
    request: Request,
    city: str = Query(...),
    days: int = Query(default=7, ge=1, le=90),
    session: AsyncSession = Depends(get_db),
):
    location = await _get_location(session, city)

    daily_avgs, distribution, accuracy, active_count = await asyncio.gather(
        get_daily_averages(session, location.location_id, days),
        get_aqi_distribution(session, location.location_id),
        get_forecast_accuracy(session, location.location_id, days),
        session.scalar(
            select(func.count()).where(
                Alert.location_id == location.location_id,
                Alert.status == "active",
            )
        ),
    )

    pdf_bytes = await asyncio.to_thread(
        _build_pdf, city, days, daily_avgs, distribution, accuracy, active_count or 0
    )
    filename = f"{city.lower().replace(' ', '-')}-aqi-report.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
