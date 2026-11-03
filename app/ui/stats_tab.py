import calendar
from datetime import date, timedelta

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QStyle, QHeaderView, QMessageBox,
    QGroupBox, QDoubleSpinBox, QAbstractSpinBox
)
from app.economics import calculate_unit_economics
from app.taxes import get_taxes_and_premiums, set_tax, set_premium, set_quarter_taxes, set_yearly_premium

class CustomDoubleSpinBox(QDoubleSpinBox):
    def textFromValue(self, value):
        return f"{value:,.2f}".replace(",", " ")

    def valueFromText(self, text):
        text = text.replace("₽", "").replace(" ", "").replace(",", ".").strip()
        try:
            return float(text)
        except ValueError:
            return 0.0

class StatsTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # ================= БЛОК НАЛОГОВ И ВЗНОСОВ =================
        fees_group = QGroupBox("Налоги и страховые взносы")
        fees_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #d0d7de;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #333;
            }
        """)
        fees_layout = QVBoxLayout(fees_group)

        spin_style = """
            QDoubleSpinBox {
                font-size: 14px;
                font-weight: bold;
                padding: 6px 10px;
                border: 1px solid #d0d7de;
                border-radius: 4px;
                background-color: #ffffff;
                color: #1f2328;
            }
            QDoubleSpinBox:focus {
                border: 1px solid #0969da;
            }
        """

        # Строка 1: Налоги (по кварталам)
        tax_row = QHBoxLayout()
        tax_row.setSpacing(10)
        tax_lbl = QLabel("Налоги:")
        tax_lbl.setStyleSheet("font-size: 14px; font-weight: bold;")
        tax_row.addWidget(tax_lbl)

        self.q1_tax = CustomDoubleSpinBox()
        self.q2_tax = CustomDoubleSpinBox()
        self.q3_tax = CustomDoubleSpinBox()
        self.q4_tax = CustomDoubleSpinBox()

        for i, spin in enumerate([self.q1_tax, self.q2_tax, self.q3_tax, self.q4_tax]):
            spin.setMaximum(99999999.99)
            spin.setDecimals(2)
            spin.setSuffix(" ₽")
            spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            spin.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            spin.setStyleSheet(spin_style)
            spin.setMinimumWidth(140)
            
            tax_row.addWidget(QLabel(f"{i+1} кв:"))
            tax_row.addWidget(spin)

        self.distribute_tax_btn = QPushButton(" Распределить налоги")
        self.distribute_tax_btn.setStyleSheet("background-color: #0969da; color: white; font-weight: bold; padding: 8px 15px; border-radius: 4px;")
        self.distribute_tax_btn.clicked.connect(self.distribute_taxes)
        tax_row.addWidget(self.distribute_tax_btn)
        tax_row.addStretch()
        fees_layout.addLayout(tax_row)

        # Строка 2: Фиксированные взносы (одно поле на год)
        prem_row = QHBoxLayout()
        prem_row.setSpacing(10)
        prem_lbl = QLabel("Фиксированные взносы (за год):")
        prem_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #333;")
        prem_row.addWidget(prem_lbl)

        self.yearly_prem_spin = CustomDoubleSpinBox()
        self.yearly_prem_spin.setMaximum(99999999.99)
        self.yearly_prem_spin.setDecimals(2)
        self.yearly_prem_spin.setSuffix(" ₽")
        self.yearly_prem_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.yearly_prem_spin.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.yearly_prem_spin.setStyleSheet(spin_style)
        self.yearly_prem_spin.setMinimumWidth(160)
        prem_row.addWidget(self.yearly_prem_spin)

        self.distribute_prem_btn = QPushButton(" Распределить на год")
        self.distribute_prem_btn.setStyleSheet("background-color: #cf222e; color: white; font-weight: bold; padding: 8px 15px; border-radius: 4px;")
        self.distribute_prem_btn.clicked.connect(self.distribute_premiums)
        prem_row.addWidget(self.distribute_prem_btn)
        prem_row.addStretch()
        fees_layout.addLayout(prem_row)

        layout.addWidget(fees_group)

        # ================= ПАНЕЛЬ УПРАВЛЕНИЯ =================
        top = QHBoxLayout()
        title_label = QLabel(f"Сводная статистика за {date.today().year} год")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        top.addWidget(title_label)
        
        self.refresh_btn = QPushButton(" Обновить")
        self.refresh_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.refresh_btn.clicked.connect(self.refresh)
        top.addWidget(self.refresh_btn)

        top.addSpacing(20)
        
        self.save_btn = QPushButton(" Сохранить изменения в таблице")
        self.save_btn.setStyleSheet("background-color: #1a7f37; color: white; font-weight: bold; padding: 8px 15px; border-radius: 4px;")
        self.save_btn.clicked.connect(self.save_table_fees)
        top.addWidget(self.save_btn)
        
        top.addStretch()
        layout.addLayout(top)
        
        # ================= ТАБЛИЦА =================
        self.table = QTableWidget()
        self.table.setColumnCount(10) 
        self.table.setHorizontalHeaderLabels([
            "Месяц", "К перечислению", "Итого к оплате", "Реклама", "Себестоимость", 
            "Прибыль\nдо вычетов", "Налог", "Взносы", "Чистая прибыль", "Маржа %"
        ])
        
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(45)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Шрифт данных
        font = QFont()
        font.setPointSize(12)
        self.table.setFont(font)
        
        # Стиль заголовков
        self.table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                background-color: #f5f7fa;
                color: #333;
                font-weight: bold;
                font-size: 12px;
                border: 1px solid #d0d7de;
                padding: 10px;
            }
        """)
        
        layout.addWidget(self.table)
        self.refresh()

    def refresh(self) -> None:
        today = date.today()
        current_year = today.year
        current_month = today.month
        
        months_ru = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
        
        taxes, premiums = get_taxes_and_premiums()
        self.monthly_data = []
        
        self.table.setRowCount(current_month + 2) 
        
        total_year_revenue = 0.0
        total_year_payout = 0.0
        total_year_ads = 0.0
        total_year_cost = 0.0
        total_year_profit = 0.0
        total_year_tax = 0.0
        total_year_prem = 0.0
        
        blue_color = "#005cc5"
        
        for i in range(current_month):
            m = i + 1
            month_str = f"{current_year}-{m:02d}"
            
            start_date = date(current_year, m, 1)
            if m == current_month:
                end_date = today - timedelta(days=1)
            else:
                _, last_day = calendar.monthrange(current_year, m)
                end_date = date(current_year, m, last_day)
                
            if start_date > end_date:
                revenue, payout, ads, profit, cost = 0.0, 0.0, 0.0, 0.0, 0.0
            else:
                try:
                    data = calculate_unit_economics(start_date.isoformat(), end_date.isoformat())
                    totals = data["totals"]
                    revenue = totals["revenue"]
                    payout = totals["payout"]
                    ads = totals["ads"]
                    cost = totals["cost"]
                    profit = totals["profit"]
                except Exception:
                    revenue, payout, ads, profit, cost = 0.0, 0.0, 0.0, 0.0, 0.0

            tax = taxes.get(month_str, 0.0)
            prem = premiums.get(month_str, 0.0)
            net_profit = profit - tax - prem
            margin = (net_profit / revenue * 100) if revenue else 0.0
            
            self.monthly_data.append({
                "month_str": month_str,
                "month_num": m,
                "revenue": revenue,
                "profit": profit
            })
            
            total_year_revenue += revenue
            total_year_payout += payout
            total_year_ads += ads
            total_year_cost += cost
            total_year_profit += profit
            total_year_tax += tax
            total_year_prem += prem
                    
            month_name = months_ru[m - 1]
            
            self._set_cell(i, 0, month_name, bold=True, align=Qt.AlignmentFlag.AlignCenter)
            self._set_cell(i, 1, f"{revenue:,.2f}".replace(",", " ") + " ₽")
            self._set_cell(i, 2, f"{payout:,.2f}".replace(",", " ") + " ₽")
            self._set_cell(i, 3, f"{round(ads):,.0f}".replace(",", " ") + " ₽", color="#cf222e")
            
            self._set_cell(i, 4, f"{cost:,.2f}".replace(",", " ") + " ₽", color=blue_color)
            
            p_color = "#1a7f37" if profit >= 0 else "#cf222e"
            self._set_cell(i, 5, f"{profit:,.2f}".replace(",", " ") + " ₽", color=p_color, bold=True)
            
            tax_str = f"{tax:,.2f}".replace(",", " ")
            tax_item = QTableWidgetItem(f"{tax_str}" if tax else "")
            tax_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            tax_item.setBackground(QColor("#f8f9fa"))
            tax_item.setForeground(QColor("#cf222e"))
            self.table.setItem(i, 6, tax_item)

            prem_str = f"{prem:,.2f}".replace(",", " ")
            prem_item = QTableWidgetItem(f"{prem_str}" if prem else "")
            prem_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            prem_item.setBackground(QColor("#f8f9fa"))
            prem_item.setForeground(QColor("#cf222e"))
            self.table.setItem(i, 7, prem_item)
            
            n_color = "#1a7f37" if net_profit >= 0 else "#cf222e"
            self._set_cell(i, 8, f"{net_profit:,.2f}".replace(",", " ") + " ₽", color=n_color, bold=True)
            self._set_cell(i, 9, f"{margin:.1f} %", color=n_color)

        # ================= ИТОГОВАЯ СТРОКА =================
        last_row = current_month
        total_net_profit = total_year_profit - total_year_tax - total_year_prem
        total_margin = (total_net_profit / total_year_revenue * 100) if total_year_revenue else 0.0
        t_p_color = "#1a7f37" if total_net_profit >= 0 else "#cf222e"
        bg = "#eaeef2"

        self._set_cell(last_row, 0, "Итого за год", bold=True, bg_color=bg, align=Qt.AlignmentFlag.AlignCenter)
        self._set_cell(last_row, 1, f"{total_year_revenue:,.2f}".replace(",", " ") + " ₽", bold=True, bg_color=bg)
        self._set_cell(last_row, 2, f"{total_year_payout:,.2f}".replace(",", " ") + " ₽", bold=True, bg_color=bg)
        self._set_cell(last_row, 3, f"{round(total_year_ads):,.0f}".replace(",", " ") + " ₽", color="#cf222e", bold=True, bg_color=bg)
        self._set_cell(last_row, 4, f"{total_year_cost:,.2f}".replace(",", " ") + " ₽", color=blue_color, bold=True, bg_color=bg)
        self._set_cell(last_row, 5, f"{total_year_profit:,.2f}".replace(",", " ") + " ₽", color=t_p_color, bold=True, bg_color=bg)
        self._set_cell(last_row, 6, f"{total_year_tax:,.2f}".replace(",", " ") + " ₽", color="#cf222e", bold=True, bg_color=bg)
        self._set_cell(last_row, 7, f"{total_year_prem:,.2f}".replace(",", " ") + " ₽", color="#cf222e", bold=True, bg_color=bg)
        self._set_cell(last_row, 8, f"{total_net_profit:,.2f}".replace(",", " ") + " ₽", color=t_p_color, bold=True, bg_color=bg)
        self._set_cell(last_row, 9, f"{total_margin:.1f} %", color=t_p_color, bold=True, bg_color=bg)

        # ================= СТРОКА СРЕДНЕГО ЗНАЧЕНИЯ =================
        avg_row = current_month + 1
        avg_net = total_net_profit / current_month if current_month > 0 else 0.0
        bg_avg = "#f0f4f8"

        # Перенос строки для "Средняя чистая прибыль в месяц"
        self._set_cell(avg_row, 0, "Средняя чистая\nприбыль в месяц", bold=True, bg_color=bg_avg, align=Qt.AlignmentFlag.AlignCenter)
        
        for col in range(1, 8):
            self._set_cell(avg_row, col, "", bg_color=bg_avg)
        self._set_cell(avg_row, 9, "", bg_color=bg_avg)
        
        self._set_cell(avg_row, 8, f"{avg_net:,.2f}".replace(",", " ") + " ₽", color=t_p_color, bold=True, bg_color=bg_avg)

        # РАВНОМЕРНОЕ РАСПРЕДЕЛЕНИЕ КОЛОНОК (КАК БЫЛО)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self._update_inputs(taxes, premiums)

    def _update_inputs(self, taxes: dict, premiums: dict):
        current_year = date.today().year
        q_taxes = [0.0, 0.0, 0.0, 0.0]
        total_prem = 0.0
        
        for m in range(1, 13):
            month_str = f"{current_year}-{m:02d}"
            q_idx = (m - 1) // 3
            q_taxes[q_idx] += taxes.get(month_str, 0.0)
            total_prem += premiums.get(month_str, 0.0)
            
        self.q1_tax.setValue(q_taxes[0])
        self.q2_tax.setValue(q_taxes[1])
        self.q3_tax.setValue(q_taxes[2])
        self.q4_tax.setValue(q_taxes[3])
        self.yearly_prem_spin.setValue(total_prem)

    def distribute_taxes(self):
        ans = QMessageBox.question(
            self, "Распределение налогов", 
            "Распределить введенные суммы налогов по кварталам пропорционально выручке?\n\n"
            "Это перезапишет текущие значения в таблице.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if ans != QMessageBox.StandardButton.Yes:
            return

        current_year = date.today().year
        spins = [self.q1_tax, self.q2_tax, self.q3_tax, self.q4_tax]
        
        for q_idx, spin in enumerate(spins):
            total_amount = spin.value()
            monthly_revenues = {}
            for m in range(q_idx * 3 + 1, q_idx * 3 + 4):
                for data in self.monthly_data:
                    if data["month_num"] == m:
                        monthly_revenues[m] = data["revenue"]
                        break
            set_quarter_taxes(q_idx + 1, current_year, total_amount, monthly_revenues)

        QMessageBox.information(self, "Готово", "Налоги успешно распределены по месяцам и сохранены.")
        self.refresh()

    def distribute_premiums(self):
        ans = QMessageBox.question(
            self, "Распределение взносов", 
            "Распределить годовую сумму взносов по всем месяцам с выручкой?\n\n"
            "Это перезапишет текущие значения в таблице.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if ans != QMessageBox.StandardButton.Yes:
            return

        current_year = date.today().year
        total_amount = self.yearly_prem_spin.value()
        monthly_revenues = {}
        for data in self.monthly_data:
            if data["revenue"] > 0:
                monthly_revenues[data["month_num"]] = data["revenue"]
        
        if not monthly_revenues:
            QMessageBox.warning(self, "Нет данных", "Нет месяцев с выручкой для распределения.")
            return

        set_yearly_premium(current_year, total_amount, monthly_revenues)
        QMessageBox.information(self, "Готово", "Взносы успешно распределены по месяцам и сохранены.")
        self.refresh()

    def save_table_fees(self):
        saved_tax = 0
        saved_prem = 0
        for i, data in enumerate(self.monthly_data):
            tax_item = self.table.item(i, 6) 
            prem_item = self.table.item(i, 7) 
            
            if tax_item:
                text = tax_item.text().strip().replace(" ", "").replace("₽", "").replace(",", ".")
                if text:
                    try:
                        set_tax(data["month_str"], float(text))
                        saved_tax += 1
                    except ValueError:
                        pass
            
            if prem_item:
                text = prem_item.text().strip().replace(" ", "").replace("₽", "").replace(",", ".")
                if text:
                    try:
                        set_premium(data["month_str"], float(text))
                        saved_prem += 1
                    except ValueError:
                        pass

        QMessageBox.information(self, "Сохранено", f"Данные сохранены: налогов {saved_tax} мес., взносов {saved_prem} мес.")
        self.refresh()

    def _set_cell(self, row, col, text, color=None, bold=False, bg_color=None, align=Qt.AlignmentFlag.AlignCenter):
        item = QTableWidgetItem(text)
        if color: 
            item.setForeground(QColor(color))
        if bg_color: 
            item.setBackground(QColor(bg_color))
        if bold:
            font = QFont()
            font.setBold(True)
            item.setFont(font)
        item.setTextAlignment(align)
        self.table.setItem(row, col, item)