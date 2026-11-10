from datetime import date
import math
import calendar
from PyQt6.QtCore import Qt, QDate, QTimer
from PyQt6.QtGui import QColor, QFont, QFontMetrics
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QFrame, QMessageBox, QTabWidget, QStyle,
    QSizePolicy
)
from app.economics import calculate_unit_economics
from app.taxes import get_taxes_and_premiums_for_period
from app.ui.month_selector import MonthSelector, CustomDateEdit

class KpiCard(QFrame):
    def __init__(self, title: str):
        super().__init__()
        self.setObjectName("KpiCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("QFrame#KpiCard { background: #f5f7fa; border: 1px solid #d0d7de; border-radius: 8px; padding: 8px; }")
        
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(2) 
        layout.setContentsMargins(8, 8, 8, 8)
        
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #666; font-size: 12px;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.value_label = QLabel("—")
        self.value_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #1f2328;")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.sub_label = QLabel("")
        self.sub_label.setStyleSheet("color: #000000; font-size: 12px;")
        self.sub_label.setTextFormat(Qt.TextFormat.RichText) 
        self.sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.sub_label)

    def set_value(self, text: str, color: str | None = None, sub_text: str | None = None) -> None:
        self.value_label.setText(text)
        if color: 
            self.value_label.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {color};")
        
        if sub_text:
            self.sub_label.setText(sub_text)
        else:
            self.sub_label.setText("")

class AdsDrrCard(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("AdsDrrCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("QFrame#AdsDrrCard { background: #f5f7fa; border: 1px solid #d0d7de; border-radius: 8px; padding: 8px; }")
        
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(15)

        left_layout = QVBoxLayout()
        left_layout.setSpacing(2)
        self.title_ads = QLabel("Реклама")
        self.title_ads.setStyleSheet("color: #666; font-size: 12px;")
        self.title_ads.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.value_ads = QLabel("—")
        self.value_ads.setStyleSheet("font-size: 20px; font-weight: bold; color: #cf222e;")
        self.value_ads.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.sub_ads = QLabel("")
        self.sub_ads.setStyleSheet("color: #000000; font-size: 12px;")
        self.sub_ads.setTextFormat(Qt.TextFormat.RichText)
        self.sub_ads.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        left_layout.addWidget(self.title_ads)
        left_layout.addWidget(self.value_ads)
        left_layout.addWidget(self.sub_ads)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setStyleSheet("color: #d0d7de;")

        right_layout = QVBoxLayout()
        right_layout.setSpacing(2)
        self.title_drr = QLabel("ДРР")
        self.title_drr.setStyleSheet("color: #666; font-size: 12px;")
        self.title_drr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.value_drr = QLabel("—")
        self.value_drr.setStyleSheet("font-size: 20px; font-weight: bold; color: #cf222e;")
        self.value_drr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.sub_drr = QLabel("")
        self.sub_drr.setStyleSheet("color: #000000; font-size: 12px;")
        self.sub_drr.setTextFormat(Qt.TextFormat.RichText)
        self.sub_drr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        right_layout.addWidget(self.title_drr)
        right_layout.addWidget(self.value_drr)
        right_layout.addWidget(self.sub_drr)

        main_layout.addLayout(left_layout)
        main_layout.addWidget(line)
        main_layout.addLayout(right_layout)

    def set_values(self, ads_text, ads_sub, drr_text, drr_sub):
        self.value_ads.setText(ads_text)
        self.sub_ads.setText(ads_sub)
        self.value_drr.setText(drr_text)
        self.sub_drr.setText(drr_sub)


class DashboardTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        self.last_known_date = QDate.currentDate()

        top = QHBoxLayout()
        top.addWidget(QLabel("С:"))
        self.date_from = CustomDateEdit()
        
        today = QDate.currentDate()
        yesterday = today.addDays(-1)
        self.date_from.setDate(yesterday)
        top.addWidget(self.date_from)

        top.addWidget(QLabel("По:"))
        self.date_to = CustomDateEdit()
        self.date_to.setDate(yesterday)
        top.addWidget(self.date_to)

        button_style = """
            QPushButton {
                background: #f5f7fa;
                border: 1px solid #d0d7de;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: bold;
                color: #1f2328;
            }
            QPushButton:hover {
                background: #eaeef2;
                border: 1px solid #0969da;
            }
            QPushButton:pressed {
                background: #d0d7de;
            }
        """

        self.btn_day = QPushButton("День")
        self.btn_day.setStyleSheet(button_style)
        self.btn_day.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_day.clicked.connect(self.set_period_day)
        top.addWidget(self.btn_day)

        self.btn_week = QPushButton("Неделя")
        self.btn_week.setStyleSheet(button_style)
        self.btn_week.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_week.clicked.connect(self.set_period_week)
        top.addWidget(self.btn_week)

        self.btn_current_month = QPushButton("Текущий месяц")
        self.btn_current_month.setStyleSheet(button_style)
        self.btn_current_month.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_current_month.clicked.connect(self.set_period_current_month)
        top.addWidget(self.btn_current_month)

        self.month_btn = QPushButton("Выбрать месяц")
        self.month_btn.setStyleSheet(button_style)
        self.month_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.month_btn.setMinimumWidth(140)
        self.month_btn.clicked.connect(self.show_month_selector)
        top.addWidget(self.month_btn)

        top.addSpacing(10)

        self.refresh_btn = QPushButton(" Обновить")
        self.refresh_btn.setStyleSheet(button_style)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.refresh_btn.clicked.connect(self.refresh)
        top.addWidget(self.refresh_btn)

        top.addStretch()
        layout.addLayout(top)

        self.month_selector = MonthSelector(self)
        self.month_selector.month_selected.connect(self.on_month_selected)

        cards_layout = QHBoxLayout()
        self.card_revenue = KpiCard("К перечислению за товар")
        self.card_payout = KpiCard("Итого к оплате")
        self.card_ads_drr = AdsDrrCard() 
        self.card_profit = KpiCard("Прибыль без учета налога")
        self.card_net_profit = KpiCard("Чистая прибыль") 
        
        for c in (self.card_revenue, self.card_payout, self.card_ads_drr, self.card_profit, self.card_net_profit): 
            cards_layout.addWidget(c, 1)
        layout.addLayout(cards_layout)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #b36b00; font-size: 12px;")
        layout.addWidget(self.status_label)

        self.tables_tabs = QTabWidget()
        
        days_tab = QWidget()
        days_layout = QVBoxLayout(days_tab)
        days_layout.setContentsMargins(0, 0, 0, 0)
        days_layout.setSpacing(0)
        
        self.table_days = QTableWidget()
        self.table_days.setColumnCount(14) 
        self.table_days.setHorizontalHeaderLabels(["Дата", "Продано (шт)", "Возвраты (шт)", "К перечислению", "Доставка", "Хранение", "Обработка", "Прочие", "Штрафы", "Корректировка", "Итого к оплате", "Себестоимость", "Реклама", "Прибыль"])
        self.table_days.horizontalHeader().setStretchLastSection(False)
        self.table_days.verticalHeader().setVisible(False)
        
        for col in [10, 11, 12, 13]:
            item = self.table_days.horizontalHeaderItem(col)
            if item:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
        
        self.table_days_total = QTableWidget(1, 14) 
        self.table_days_total.horizontalHeader().setVisible(False)
        self.table_days_total.verticalHeader().setVisible(False)
        self.table_days_total.setFixedHeight(35)
        self.table_days_total.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table_days_total.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_days_total.setStyleSheet("QTableWidget { border: 1px solid #d0d7de; background: #eaeef2; border-top: none; }")
        self.table_days_total.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table_days_total.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        days_layout.addWidget(self.table_days)
        days_layout.addWidget(self.table_days_total)
        self.tables_tabs.addTab(days_tab, "По дням")

        articles_tab = QWidget()
        articles_layout = QVBoxLayout(articles_tab)
        articles_layout.setContentsMargins(0, 0, 0, 0)
        articles_layout.setSpacing(0)
        
        self.table_articles = QTableWidget()
        self.table_articles.setColumnCount(15) 
        self.table_articles.setHorizontalHeaderLabels(["Наименование", "Продано (шт)", "Возвраты (шт)", "К перечислению", "Доставка", "Хранение", "Обработка", "Прочие", "Штрафы", "Корректировка", "Итого к оплате", "Себестоимость", "Реклама", "Прибыль", "ДРР %"])
        self.table_articles.horizontalHeader().setStretchLastSection(False)
        self.table_articles.verticalHeader().setVisible(False)
        
        for col in [10, 11, 12, 13]:
            item = self.table_articles.horizontalHeaderItem(col)
            if item:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
        
        self.table_articles_total = QTableWidget(1, 15) 
        self.table_articles_total.horizontalHeader().setVisible(False)
        self.table_articles_total.verticalHeader().setVisible(False)
        self.table_articles_total.setFixedHeight(35)
        self.table_articles_total.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table_articles_total.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_articles_total.setStyleSheet("QTableWidget { border: 1px solid #d0d7de; background: #eaeef2; border-top: none; }")
        self.table_articles_total.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table_articles_total.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        articles_layout.addWidget(self.table_articles)
        articles_layout.addWidget(self.table_articles_total)
        self.tables_tabs.addTab(articles_tab, "По артикулам")

        layout.addWidget(self.tables_tabs)

        self.table_days.horizontalScrollBar().valueChanged.connect(self.table_days_total.horizontalScrollBar().setValue)
        self.table_days_total.horizontalScrollBar().valueChanged.connect(self.table_days.horizontalScrollBar().setValue)

        self.table_articles.horizontalScrollBar().valueChanged.connect(self.table_articles_total.horizontalScrollBar().setValue)
        self.table_articles_total.horizontalScrollBar().valueChanged.connect(self.table_articles.horizontalScrollBar().setValue)

        self.refresh()

        # ================= ТАЙМЕР АВТООБНОВЛЕНИЯ ДАШБОРДА =================
        # Каждые 15 минут проверяем, не сменился ли день, и обновляем данные
        self.auto_refresh_timer = QTimer(self)
        self.auto_refresh_timer.timeout.connect(self.auto_refresh_check)
        self.auto_refresh_timer.start(15 * 60 * 1000)

    def auto_refresh_check(self):
        current_date = QDate.currentDate()
        
        # Если наступил новый день (например, программа работала всю ночь)
        if current_date != self.last_known_date:
            self.last_known_date = current_date
            
            # Если пользователь смотрел на "Вчера" (даты одинаковые), то сдвигаем их на новое "Вчера"
            if self.month_btn.text() == "Выбрать месяц" and self.date_from.date() == self.date_to.date():
                yesterday = current_date.addDays(-1)
                self.date_from.setDate(yesterday)
                self.date_to.setDate(yesterday)
        
        # В любом случае обновляем данные на экране
        self.refresh()

    def show_month_selector(self):
        self.month_selector.show_at(self.month_btn)

    def on_month_selected(self, year, month):
        qdate_start = QDate(year, month, 1)
        current_date = QDate.currentDate()
        
        if year == current_date.year() and month == current_date.month():
            qdate_end = current_date.addDays(-1)
            if qdate_end < qdate_start:
                qdate_end = qdate_start
        else:
            qdate_end = qdate_start.addMonths(1).addDays(-1)
            
        self.date_from.setDate(qdate_start)
        self.date_to.setDate(qdate_end)
        
        months_ru = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
        self.month_btn.setText(f"{months_ru[month-1]} {year}")
        self.month_selector.set_active_month(month)
        self.refresh()

    def set_period_day(self):
        self.month_btn.setText("Выбрать месяц")
        yesterday = QDate.currentDate().addDays(-1)
        self.date_from.setDate(yesterday)
        self.date_to.setDate(yesterday)
        self.refresh()

    def set_period_week(self):
        self.month_btn.setText("Выбрать месяц")
        today = QDate.currentDate()
        yesterday = today.addDays(-1)
        week_ago = yesterday.addDays(-6)
        self.date_from.setDate(week_ago)
        self.date_to.setDate(yesterday)
        self.refresh()

    def set_period_current_month(self):
        self.on_month_selected(QDate.currentDate().year(), QDate.currentDate().month())

    def _set_cell(self, table, row, col, text, color=None, bold=False, bg_color=None):
        item = QTableWidgetItem(text)
        if color: item.setForeground(QColor(color))
        if bg_color: item.setBackground(QColor(bg_color))
        if bold:
            font = QFont()
            font.setBold(True)
            item.setFont(font)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter) 
        table.setItem(row, col, item)

    def _adjust_column_widths(self, table):
        table.resizeColumnsToContents()
        font_metrics = QFontMetrics(table.horizontalHeader().font())
        narrow_cols = [1, 2, 9]
        
        for col in range(table.columnCount()):
            if col in narrow_cols:
                header_text = table.horizontalHeaderItem(col).text()
                width = font_metrics.horizontalAdvance(header_text) + 10
                table.setColumnWidth(col, width)
            else:
                table.setColumnWidth(col, table.columnWidth(col) + 25)

    def refresh(self) -> None:
        qdate_from = self.date_from.date()
        qdate_to = self.date_to.date()

        date_from = qdate_from.toString("yyyy-MM-dd")
        date_to = qdate_to.toString("yyyy-MM-dd")
        
        if date_from > date_to:
            QMessageBox.warning(self, "Ошибка дат", "Дата начала не может быть позже даты окончания.")
            return

        if self.month_btn.text() == "Выбрать месяц" and qdate_from.daysTo(qdate_to) <= 6:
            self.card_net_profit.hide()
        else:
            self.card_net_profit.show()

        try:
            data = calculate_unit_economics(date_from, date_to)
            period_tax, period_prem = get_taxes_and_premiums_for_period(date_from, date_to)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка расчёта", str(e))
            return

        totals = data["totals"]
        num_days = len(data["by_day"])
        
        profit_color = "#1a7f37" if totals["profit"] >= 0 else "#cf222e"
        blue_color = "#005cc5"
        
        net_profit = totals["profit"] - period_tax - period_prem
        net_profit_color = "#1a7f37" if net_profit >= 0 else "#cf222e"

        drr_val = (totals["ads"] / totals["ads_total_price"] * 100) if totals["ads_total_price"] > 0 else 0.0

        rev_str = f"{totals['revenue']:,.2f}".replace(",", " ")
        pay_str = f"{totals['payout']:,.2f}".replace(",", " ")
        ads_str = f"{round(totals['ads']):,.0f}".replace(",", " ")
        prof_str = f"{totals['profit']:,.2f}".replace(",", " ")
        net_str = f"{net_profit:,.2f}".replace(",", " ")
        
        if num_days > 0:
            avg_ads = f"{round(totals['ads'] / num_days):,.0f}".replace(",", " ")
            avg_profit = f"{totals['profit'] / num_days:,.2f}".replace(",", " ")
            avg_net_val = net_profit / num_days
            avg_net = f"{avg_net_val:,.2f}".replace(",", " ")
            
            days_in_month = calendar.monthrange(qdate_to.year(), qdate_to.month())[1]
            forecast_net_val = avg_net_val * days_in_month
            forecast_net_str = f"{forecast_net_val:,.2f}".replace(",", " ")
            
            sub_ads = f"Среднее в день: <span style='color:#cf222e; font-weight: bold;'>{avg_ads} ₽</span>"
            sub_profit = f"Среднее в день: <span style='color:{profit_color}; font-weight: bold;'>{avg_profit} ₽</span>"
            
            sub_net = f"Среднее в день: <span style='color:{net_profit_color}; font-weight: bold;'>{avg_net} ₽</span>"
            sub_net += f"<br>Прогноз на месяц: <span style='color:#0969da; font-weight: bold;'>{forecast_net_str} ₽</span>"
        else:
            sub_ads = "Среднее в день: —"
            sub_profit = "Среднее в день: —"
            sub_net = "Среднее в день: —<br>Прогноз на месяц: —"
        
        self.card_revenue.set_value(f"{rev_str} ₽")
        self.card_payout.set_value(f"{pay_str} ₽")
        
        self.card_ads_drr.set_values(
            ads_text=f"{ads_str} ₽", ads_sub=sub_ads,
            drr_text=f"{drr_val:.1f} %", drr_sub="от суммы заказов"
        )
        
        self.card_profit.set_value(f"{prof_str} ₽", color=profit_color, sub_text=sub_profit)
        self.card_net_profit.set_value(f"{net_str} ₽", color=net_profit_color, sub_text=sub_net)

        if totals["articles_without_cost"]:
            self.status_label.setText(f"⚠ Нет себестоимости у артикулов: {', '.join(str(x) for x in totals['articles_without_cost'])}.")
        else:
            self.status_label.setText("")

        t_p_color = profit_color

        rows_d = data["by_day"]
        self.table_days.setRowCount(len(rows_d))
        
        for i, d in enumerate(rows_d):
            raw_date = d["date"]
            formatted_date = f"{raw_date[8:10]}.{raw_date[5:7]}.{raw_date[0:4]}"
            
            self._set_cell(self.table_days, i, 0, formatted_date)
            self._set_cell(self.table_days, i, 1, str(d["qty"]))
            self._set_cell(self.table_days, i, 2, str(d["return_qty"]))
            self._set_cell(self.table_days, i, 3, f"{d['revenue']:,.2f}".replace(",", " "))
            self._set_cell(self.table_days, i, 4, f"{d['delivery']:,.2f}".replace(",", " "))
            self._set_cell(self.table_days, i, 5, f"{d['storage']:,.2f}".replace(",", " "))
            self._set_cell(self.table_days, i, 6, f"{d['processing']:,.2f}".replace(",", " "))
            self._set_cell(self.table_days, i, 7, f"{d['other']:,.2f}".replace(",", " "))
            self._set_cell(self.table_days, i, 8, f"{d['penalty']:,.2f}".replace(",", " "))
            self._set_cell(self.table_days, i, 9, f"{d['correction']:,.2f}".replace(",", " "))
            
            self._set_cell(self.table_days, i, 10, f"{d['payout']:,.2f}".replace(",", " "), bold=True)
            self._set_cell(self.table_days, i, 11, f"{d['cost']:,.2f}".replace(",", " "), color=blue_color, bold=True)
            self._set_cell(self.table_days, i, 12, f"{round(d['ads']):,.0f}".replace(",", " "), color="#cf222e", bold=True)
            
            p_color = "#1a7f37" if d["profit"] >= 0 else "#cf222e"
            self._set_cell(self.table_days, i, 13, f"{d['profit']:,.2f}".replace(",", " "), color=p_color, bold=True)
            
        self._adjust_column_widths(self.table_days)

        self._set_cell(self.table_days_total, 0, 0, "ИТОГО", bold=True)
        self._set_cell(self.table_days_total, 0, 1, str(totals["qty"]), bold=True)
        self._set_cell(self.table_days_total, 0, 2, str(totals["return_qty"]), bold=True)
        self._set_cell(self.table_days_total, 0, 3, f"{totals['revenue']:,.2f}".replace(",", " "), bold=True)
        self._set_cell(self.table_days_total, 0, 4, f"{totals['delivery']:,.2f}".replace(",", " "), bold=True)
        self._set_cell(self.table_days_total, 0, 5, f"{totals['storage']:,.2f}".replace(",", " "), bold=True)
        self._set_cell(self.table_days_total, 0, 6, f"{totals['processing']:,.2f}".replace(",", " "), bold=True)
        self._set_cell(self.table_days_total, 0, 7, f"{totals['other']:,.2f}".replace(",", " "), bold=True)
        self._set_cell(self.table_days_total, 0, 8, f"{totals['penalty']:,.2f}".replace(",", " "), bold=True)
        self._set_cell(self.table_days_total, 0, 9, f"{totals['correction']:,.2f}".replace(",", " "), bold=True)
        self._set_cell(self.table_days_total, 0, 10, f"{totals['payout']:,.2f}".replace(",", " "), bold=True)
        self._set_cell(self.table_days_total, 0, 11, f"{totals['cost']:,.2f}".replace(",", " "), color=blue_color, bold=True)
        self._set_cell(self.table_days_total, 0, 12, f"{round(totals['ads']):,.0f}".replace(",", " "), color="#cf222e", bold=True)
        self._set_cell(self.table_days_total, 0, 13, f"{totals['profit']:,.2f}".replace(",", " "), color=t_p_color, bold=True)

        for col in range(self.table_days.columnCount()):
            self.table_days_total.setColumnWidth(col, self.table_days.columnWidth(col))

        rows_a = data["by_article"]
        self.table_articles.setRowCount(len(rows_a))
        
        for i, a in enumerate(rows_a):
            name = ("⚠ " if not a["has_cost"] else "") + a["name"]
            self._set_cell(self.table_articles, i, 0, name)
            self._set_cell(self.table_articles, i, 1, str(a["qty"]))
            self._set_cell(self.table_articles, i, 2, str(a["return_qty"]))
            self._set_cell(self.table_articles, i, 3, f"{a['revenue']:,.2f}".replace(",", " "))
            self._set_cell(self.table_articles, i, 4, f"{a['delivery']:,.2f}".replace(",", " "))
            self._set_cell(self.table_articles, i, 5, f"{a['storage']:,.2f}".replace(",", " "))
            self._set_cell(self.table_articles, i, 6, f"{a['processing']:,.2f}".replace(",", " "))
            self._set_cell(self.table_articles, i, 7, f"{a['other']:,.2f}".replace(",", " "))
            self._set_cell(self.table_articles, i, 8, f"{a['penalty']:,.2f}".replace(",", " "))
            self._set_cell(self.table_articles, i, 9, f"{a['correction']:,.2f}".replace(",", " "))
            
            self._set_cell(self.table_articles, i, 10, f"{a['payout']:,.2f}".replace(",", " "), bold=True)
            self._set_cell(self.table_articles, i, 11, f"{a['cost']:,.2f}".replace(",", " "), color=blue_color, bold=True)
            self._set_cell(self.table_articles, i, 12, f"{round(a['ads']):,.0f}".replace(",", " "), color="#cf222e", bold=True)
            
            p_color = "#1a7f37" if a["profit"] >= 0 else "#cf222e"
            self._set_cell(self.table_articles, i, 13, f"{a['profit']:,.2f}".replace(",", " "), color=p_color, bold=True)
            self._set_cell(self.table_articles, i, 14, f"{a['drr']:.1f}")

        self._adjust_column_widths(self.table_articles)

        self._set_cell(self.table_articles_total, 0, 0, "ИТОГО", bold=True)
        self._set_cell(self.table_articles_total, 0, 1, str(totals["qty"]), bold=True)
        self._set_cell(self.table_articles_total, 0, 2, str(totals["return_qty"]), bold=True)
        self._set_cell(self.table_articles_total, 0, 3, f"{totals['revenue']:,.2f}".replace(",", " "), bold=True)
        self._set_cell(self.table_articles_total, 0, 4, f"{totals['delivery']:,.2f}".replace(",", " "), bold=True)
        self._set_cell(self.table_articles_total, 0, 5, f"{totals['storage']:,.2f}".replace(",", " "), bold=True)
        self._set_cell(self.table_articles_total, 0, 6, f"{totals['processing']:,.2f}".replace(",", " "), bold=True)
        self._set_cell(self.table_articles_total, 0, 7, f"{totals['other']:,.2f}".replace(",", " "), bold=True)
        self._set_cell(self.table_articles_total, 0, 8, f"{totals['penalty']:,.2f}".replace(",", " "), bold=True)
        self._set_cell(self.table_articles_total, 0, 9, f"{totals['correction']:,.2f}".replace(",", " "), bold=True)
        self._set_cell(self.table_articles_total, 0, 10, f"{totals['payout']:,.2f}".replace(",", " "), bold=True)
        self._set_cell(self.table_articles_total, 0, 11, f"{totals['cost']:,.2f}".replace(",", " "), color=blue_color, bold=True)
        self._set_cell(self.table_articles_total, 0, 12, f"{round(totals['ads']):,.0f}".replace(",", " "), color="#cf222e", bold=True)
        self._set_cell(self.table_articles_total, 0, 13, f"{totals['profit']:,.2f}".replace(",", " "), color=t_p_color, bold=True)
        self._set_cell(self.table_articles_total, 0, 14, f"{drr_val:.1f}", color="#cf222e", bold=True)

        for col in range(self.table_articles.columnCount()):
            self.table_articles_total.setColumnWidth(col, self.table_articles.columnWidth(col))