"""PDF credit assessment report (ReportLab).

The report only restates computed figures and rule-based observations. It makes
no recommendation to lend or invest and carries the scoring disclaimer.
Synthetic data is marked with a banner on every page.
"""

from __future__ import annotations

import datetime as dt
import io
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_LEFT  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from . import config as C  # noqa: E402
from .financial_ratios import format_ratio  # noqa: E402
from .pipeline import Analysis, company_assessment  # noqa: E402
from .stress_testing import run_stress  # noqa: E402
from .trend_analysis import trend_frame  # noqa: E402

NAVY = colors.HexColor("#1f3a5f")
GRID = colors.HexColor("#c9cfd6")
LIGHT = colors.HexColor("#eef2f6")
RED = colors.HexColor("#b42318")
PAGE_W, PAGE_H = A4
MARGIN = 16 * mm
CONTENT_W = PAGE_W - 2 * MARGIN


def _styles():
    ss = getSampleStyleSheet()
    base = ParagraphStyle("base", parent=ss["Normal"], fontName="Helvetica", fontSize=9, leading=12)
    return {
        "title": ParagraphStyle("title", parent=base, fontName="Helvetica-Bold", fontSize=16, leading=20,
                                textColor=NAVY, spaceAfter=4),
        "h2": ParagraphStyle("h2", parent=base, fontName="Helvetica-Bold", fontSize=11.5, leading=15,
                             textColor=NAVY, spaceBefore=8, spaceAfter=4),
        "body": base,
        "small": ParagraphStyle("small", parent=base, fontSize=7.5, leading=9.5, textColor=colors.HexColor("#444")),
        "cell": ParagraphStyle("cell", parent=base, fontSize=8, leading=10, alignment=TA_LEFT),
        "cellb": ParagraphStyle("cellb", parent=base, fontName="Helvetica-Bold", fontSize=8, leading=10,
                                textColor=colors.white),
        "banner": ParagraphStyle("banner", parent=base, fontName="Helvetica-Bold", fontSize=8.5,
                                 textColor=colors.white),
    }


def _table(data: list[list], widths: list[float], st: dict, zebra: bool = True) -> Table:
    """Wrap every cell in a Paragraph so long text wraps instead of overflowing the page."""
    rows = []
    for i, row in enumerate(data):
        style = st["cellb"] if i == 0 else st["cell"]
        rows.append([Paragraph(str(v), style) for v in row])
    t = Table(rows, colWidths=widths, repeatRows=1)
    cmds = [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("GRID", (0, 0), (-1, -1), 0.4, GRID),
            ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if zebra:
        cmds += [("BACKGROUND", (0, i), (-1, i), LIGHT) for i in range(2, len(rows), 2)]
    t.setStyle(TableStyle(cmds))
    return t


def _money(v: float, units: str = "") -> str:
    return "n/a" if pd.isna(v) else f"{v:,.1f}"


def _trend_chart(tf: pd.DataFrame, units: str) -> io.BytesIO:
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.0))
    yrs = tf["fiscal_year"].astype(str)
    ax = axes[0]
    ax.bar(yrs, tf["revenue"], color="#8fa9c7", label="Revenue")
    ax.plot(yrs, tf["operating_cash_flow"], color="#1f3a5f", marker="o", label="Operating cash flow")
    ax.plot(yrs, tf["net_profit"], color="#b42318", marker="s", label="Net profit")
    ax.axhline(0, color="#666", lw=0.6)
    ax.set_title(f"Revenue, profit and cash flow ({units})", fontsize=9)
    ax.tick_params(labelsize=7.5)
    ax.legend(fontsize=6.5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3)
    ax = axes[1]
    ax.plot(yrs, tf["health_score"], color="#1f3a5f", marker="o")
    ax.set_ylim(0, 100)
    ax.set_title("Illustrative financial health score", fontsize=9)
    ax.tick_params(labelsize=7.5)
    for side in ("top", "right"):
        axes[0].spines[side].set_visible(False)
        axes[1].spines[side].set_visible(False)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=170)
    plt.close(fig)
    buf.seek(0)
    return buf


def build_pdf(a: Analysis, company: str, year: int, path: Path | str,
              scenarios: list[C.StressScenario] | None = None) -> Path:
    """Write the PDF credit assessment report for one company-year and return its path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    st = _styles()
    x = company_assessment(a, company, year)
    meta, score, r = x["meta"], x["score"], x["ratios"]
    units = f"{meta['currency']} {meta['units']}"
    synthetic = str(meta["data_type"]).upper() == "SYNTHETIC"
    generated = dt.datetime.now().strftime("%d %b %Y %H:%M")

    def on_page(canvas, doc):
        canvas.saveState()
        if synthetic:
            canvas.setFillColor(RED)
            canvas.rect(0, PAGE_H - 9 * mm, PAGE_W, 9 * mm, fill=1, stroke=0)
            canvas.setFillColor(colors.white)
            canvas.setFont("Helvetica-Bold", 8.5)
            canvas.drawCentredString(PAGE_W / 2, PAGE_H - 6 * mm,
                                     "SYNTHETIC DEMONSTRATION DATA - fictional company - not an assessment of any real company")
        canvas.setFillColor(colors.HexColor("#666"))
        canvas.setFont("Helvetica", 7)
        canvas.drawString(MARGIN, 9 * mm, f"CorporateRisk credit health check | {company} | FY{year} | "
                                          f"generated {generated}")
        canvas.drawRightString(PAGE_W - MARGIN, 9 * mm, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                            topMargin=MARGIN + (6 * mm if synthetic else 0), bottomMargin=16 * mm,
                            title=f"Credit assessment - {company} FY{year}", author="CorporateRisk")
    story = []

    # 1-2. Title block
    story.append(Paragraph("Corporate Credit Health Assessment", st["title"]))
    story.append(Paragraph(f"<b>{company}</b> | Sector: {meta['sector']} | Financial year ending "
                           f"March {year} (FY{year}) | {meta['statement_basis'].title()} statements | "
                           f"Amounts in {units} | Report date: {generated}", st["body"]))
    story.append(Spacer(1, 6))

    # 3-5. Executive summary and score
    story.append(Paragraph("Executive summary", st["h2"]))
    story.append(Paragraph(x["commentary"], st["body"]))
    story.append(Spacer(1, 6))
    z = x["altman"]
    z_text = (f"{z['z_score']:.2f} ({z['zone']} zone; {z['variant_label']})" if z["status"] == "ok"
              else f"Not computable ({z['note']})")
    summary = [["Measure", "Result"],
               ["Financial health score (0-100, illustrative)", f"{score['health_score']:.1f}"],
               ["Risk classification (illustrative band)", score["risk_category"]],
               ["Share of scoring weight assessed", f"{score['weight_coverage']:.0%}"],
               ["Altman Z-score (distress screen)", z_text]]
    story.append(_table(summary, [CONTENT_W * 0.45, CONTENT_W * 0.55], st))
    story.append(Spacer(1, 4))
    dims = [["Dimension", "Weight", "Score (0-100)"]]
    cfg = C.ScoringConfig()
    for d in C.DIMENSIONS:
        v = score[f"score_{d}"]
        dims.append([d, f"{cfg.weights[d]:.0%}", "not scored" if pd.isna(v) else f"{v:.1f}"])
    story.append(_table(dims, [CONTENT_W * 0.5, CONTENT_W * 0.2, CONTENT_W * 0.3], st))

    # 6. Ratio table (up to three years)
    hist = a.ratios[(a.ratios["company"] == company) & (a.ratios["fiscal_year"] <= year)] \
        .sort_values("fiscal_year").tail(3)
    yrs = hist["fiscal_year"].tolist()
    story.append(Paragraph("Financial ratios", st["h2"]))
    rt = [["Ratio", "Dimension"] + [f"FY{y}" for y in yrs]]
    for key, (name, dim, direction) in C.RATIOS.items():
        vals = []
        for _, h in hist.iterrows():
            v = format_ratio(key, h[key])
            if h[f"{key}__status"] == "adverse_undefined":
                v = "n/m (adverse)"
            elif h[f"{key}__status"] == "not_applicable":
                v = "n/a (no debt/interest)"
            vals.append(v)
        rt.append([f"{name} ({'higher' if direction == 'higher' else 'lower'} is better)", dim] + vals)
    yw = (CONTENT_W * 0.40) / max(len(yrs), 1)
    story.append(_table(rt, [CONTENT_W * 0.38, CONTENT_W * 0.22] + [yw] * len(yrs), st))
    story.append(Paragraph("n/m = not meaningful because the denominator is zero or negative for an adverse "
                           "reason (e.g. negative equity, EBITDA <= 0); scored as the weakest outcome. "
                           "n/a = not applicable; excluded from scoring.", st["small"]))

    # 7. Trends
    tf = trend_frame(a.ratios, a.scores, company)
    tf = tf[tf["fiscal_year"] <= year]
    story.append(KeepTogether([Paragraph("Financial trends", st["h2"]),
                               Image(_trend_chart(tf, units), width=CONTENT_W, height=CONTENT_W * 3.0 / 8.2)]))
    items = [["Item"] + [f"FY{y}" for y in tf["fiscal_year"]]]
    for col, label in (("revenue", "Revenue"), ("net_profit", "Net profit"), ("total_debt", "Interest-bearing debt"),
                       ("operating_cash_flow", "Operating cash flow"), ("free_cash_flow", "Free cash flow")):
        items.append([f"{label} ({units})"] + [_money(v, units) for v in tf[col]])
    n = len(tf)
    story.append(_table(items, [CONTENT_W * 0.30] + [CONTENT_W * 0.70 / max(n, 1)] * n, st))

    # 8-9. Strengths and risks
    story.append(Paragraph("Key strengths", st["h2"]))
    for s in x["strengths"][:6] or ["No ratio reached the 'strong' range on the illustrative scale."]:
        story.append(Paragraph(f"&bull; {s}", st["body"]))
    story.append(Paragraph("Key financial risks", st["h2"]))
    risks = x["weaknesses"][:6] + [f"{s['signal']}: {s['evidence']}" for s in x["signals"]]
    for s in risks or ["No ratio fell into the 'weak' range and no multi-year warning signal was triggered."]:
        story.append(Paragraph(f"&bull; {s}", st["body"]))

    # 10. Stress testing
    story.append(PageBreak())
    story.append(Paragraph("Stress testing summary (illustrative)", st["h2"]))
    sres = run_stress(a.data, company, year, scenarios)
    srows = [["Scenario", "Shock", "Interest cover", "Net debt / EBITDA", "Net margin", "FCF", "Health score"]]
    for _, s in sres.iterrows():
        shock = (f"Revenue {s['revenue_change']:+.0%}, EBITDA margin {s['ebitda_margin_change'] * 100:+.0f} pp, "
                 f"interest {s['interest_change']:+.0%}")
        ndx = "n/m (EBITDA <= 0)" if s["net_debt_to_ebitda__status"] == "adverse_undefined" \
            else format_ratio("net_debt_to_ebitda", s["net_debt_to_ebitda"])
        icr = "n/a" if s["interest_coverage__status"] == "not_applicable" \
            else format_ratio("interest_coverage", s["interest_coverage"])
        srows.append([s["scenario"], shock, icr, ndx, format_ratio("net_profit_margin", s["net_profit_margin"]),
                      _money(s["free_cash_flow"], units), f"{s['health_score']:.1f} ({s['risk_category']})"])
    story.append(_table(srows, [CONTENT_W * w for w in (0.14, 0.27, 0.11, 0.13, 0.10, 0.10, 0.15)], st))
    story.append(Paragraph("Shocks are applied to revenue, EBITDA margin and interest cost; EBIT, profit, tax, "
                           "operating and free cash flow and all ratios are recomputed. The balance sheet, D&amp;A, "
                           "capital expenditure and working capital are held constant.", st["small"]))

    # 11. Limitations
    story.append(Paragraph("Limitations", st["h2"]))
    lims = [C.DISCLAIMER,
            "Weights, ratio anchors and score bands are educational assumptions, not calibrated to observed defaults.",
            "The Altman Z-score zones were derived from historical, mostly US samples; they are a screening "
            "prompt, not a forecast of default.",
            "Ratios use annual reported figures and cannot capture intra-year liquidity, off-balance-sheet "
            "commitments, guarantees, contingent liabilities or the quality of earnings.",
            "Cross-sector comparisons can mislead because normal ratio ranges differ by industry."]
    if synthetic:
        lims.insert(0, C.SYNTHETIC_NOTICE)
    for s in lims:
        story.append(Paragraph(f"&bull; {s}", st["body"]))

    # 12. Data sources
    story.append(Paragraph("Data sources", st["h2"]))
    src = a.data.loc[a.data["company"] == company]
    from .data_loader import load_sources  # local import keeps module import light
    sources = load_sources()
    srow = sources[sources["company"] == company]
    if not srow.empty:
        for _, s in srow.iterrows():
            story.append(Paragraph(f"&bull; {s['source']} - {s['url_or_reference']} "
                                   f"({s.get('statement_basis', '')}, {s.get('units', '')}). {s.get('notes', '')}",
                                   st["body"]))
    else:
        story.append(Paragraph("&bull; No source recorded in data/sources.csv for this company.", st["body"]))
    story.append(Paragraph(f"Fiscal years in input: FY{src['fiscal_year'].min()}-FY{src['fiscal_year'].max()}; "
                           f"basis: {meta['statement_basis']}; units: {units}.", st["small"]))

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return path
