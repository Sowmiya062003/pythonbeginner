"""
bill_generator.py - PDF Bill creation module for Doraemon 21st Cen Eateries.
Generates styled ReportLab PDF bills including logo, token number, customer details,
itemized costs, and grand total.
"""

import os
import re
import datetime
import logging

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

logger = logging.getLogger("bill_generator")


class BillGenerator:
    """Generates styled PDF receipts."""

    RESTAURANT_NAME = "Doraemon 21st Cen Eateries"

    @staticmethod
    def generate_pdf(bill_number, token_number, customer_name, table_number, order_summary, total_amount, logo_path):
        """
        Creates PDF bill: Bill_<BillNumber>_<CustomerName>_<TableNumber>.pdf
        """
        clean_name = re.sub(r'[^a-zA-Z0-9]', '', customer_name)
        clean_table = re.sub(r'[^a-zA-Z0-9]', '', table_number)
        filename = f"Bill_{bill_number}_{clean_name}_T{clean_table}.pdf"
        filepath = os.path.abspath(filename)

        if not HAS_REPORTLAB:
            logger.error("ReportLab library missing. Using text fallback.")
            return BillGenerator.generate_text_fallback(filepath.replace('.pdf', '.txt'), bill_number, token_number, customer_name, table_number, order_summary, total_amount)

        doc = SimpleDocTemplate(filepath, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
        story = []

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=20,
            textColor=colors.HexColor('#2C3E50'),
            alignment=1,
            spaceAfter=4
        )

        meta_style = ParagraphStyle(
            'MetaStyle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            textColor=colors.HexColor('#34495E'),
            leading=14
        )

        # Header Block
        header_data = []
        if logo_path and os.path.exists(logo_path) and HAS_PIL:
            try:
                logo_img = RLImage(logo_path, width=65, height=65)
                header_text = Paragraph(f"<b>{BillGenerator.RESTAURANT_NAME}</b><br/><font size=9 color='#7F8C8D'>21st Century Taste & Quality Guaranteed</font>", title_style)
                header_data = [[logo_img, header_text]]
            except Exception:
                header_text = Paragraph(f"<b>{BillGenerator.RESTAURANT_NAME}</b>", title_style)
                header_data = [[header_text]]
        else:
            header_text = Paragraph(f"<b>{BillGenerator.RESTAURANT_NAME}</b>", title_style)
            header_data = [[header_text]]

        header_table = Table(header_data, colWidths=[75, 445] if len(header_data[0]) > 1 else [520])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 12))

        # Divider
        divider = Table([['']], colWidths=[520])
        divider.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, -1), 1.5, colors.HexColor('#2C3E50')),
        ]))
        story.append(divider)
        story.append(Spacer(1, 10))

        # Metadata Table
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        meta_left = Paragraph(
            f"<b>Customer Name:</b> {customer_name}<br/>"
            f"<b>Table Number:</b> {table_number}<br/>"
            f"<b>Bill Number:</b> {bill_number}", meta_style
        )
        meta_right = Paragraph(
            f"<font color='#E74C3C' size=14><b>TOKEN #{token_number}</b></font><br/>"
            f"<b>Date & Time:</b> {now_str}", meta_style
        )

        meta_table = Table([[meta_left, meta_right]], colWidths=[260, 260])
        meta_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 14))

        # Itemized Order Table
        table_data = [["#", "Item Description", "Category", "Qty", "Unit Price", "Total (RS.)"]]

        idx = 1
        for item in order_summary:
            table_data.append([
                str(idx),
                item['name'],
                item.get('category', 'Food'),
                str(item['qty']),
                f"RS. {item['price']:.2f}",
                f"RS. {item['total']:.2f}"
            ])
            idx += 1

        table_data.append(["", "", "", "", "TOTAL BILL:", f"RS. {total_amount:.2f}"])

        order_table = Table(table_data, colWidths=[30, 200, 90, 40, 80, 80])
        order_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -2), 0.5, colors.HexColor('#BDC3C7')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#ECF0F1')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 11),
            ('LINEABOVE', (0, -1), (-1, -1), 1.5, colors.HexColor('#2C3E50')),
        ]))
        story.append(order_table)
        story.append(Spacer(1, 20))

        # Footer
        footer_style = ParagraphStyle(
            'FooterStyle',
            parent=styles['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=10,
            textColor=colors.HexColor('#27AE60'),
            alignment=1
        )
        story.append(Paragraph("Thank you for dining at Doraemon 21st Cen Eateries! Come again! 🙏", footer_style))

        doc.build(story)
        logger.info(f"Generated PDF bill successfully: {filepath}")
        return filepath

    @staticmethod
    def generate_text_fallback(filepath, bill_number, token_number, customer_name, table_number, order_summary, total_amount):
        """Fallback plain text generator."""
        lines = []
        lines.append("===================================================\n")
        lines.append(f"          {BillGenerator.RESTAURANT_NAME}          \n")
        lines.append("===================================================\n")
        lines.append(f" TOKEN NUMBER:  #{token_number}\n")
        lines.append(f" Bill Number:   {bill_number}\n")
        lines.append(f" Customer Name: {customer_name}\n")
        lines.append(f" Table Number:  {table_number}\n")
        lines.append(f" Date & Time:   {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append("---------------------------------------------------\n")
        lines.append(f" {'Item':<18} {'Qty':<6} {'Price':<10} {'Total':>8}\n")
        lines.append("---------------------------------------------------\n")
        for item in order_summary:
            lines.append(f" {item['name']:<18} {item['qty']:<6} RS.{item['price']:<7.2f} RS.{item['total']:>6.2f}\n")
        lines.append("---------------------------------------------------\n")
        lines.append(f" TOTAL AMOUNT:                         RS. {total_amount:>6.2f}\n")
        lines.append("===================================================\n")
        lines.append("       Thank you for dining with us! Come again!    \n")
        lines.append("===================================================\n")

        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(lines)
        return filepath
