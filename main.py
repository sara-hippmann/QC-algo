# region imports
from AlgorithmImports import *
from DualMomentumAlphaModel import *


# endregion

class SectorDualMomentumStrategy(QCAlgorithm):
    undesired_symbols_from_previous_deployment = []
    checked_symbols_from_previous_deployment = False

    def initialize(self):
        self.set_start_date(2022, 12, 4)
        self.set_end_date(2024, 6, 5)
        self.set_cash(100000)

        self.universe_settings.data_normalization_mode = DataNormalizationMode.RAW
        self.universe_settings.asynchronous = True
        self.add_universe(self.universe.etf("SPY", self.universe_settings, self._etf_constituents_filter))

        self.add_alpha(DualMomentumAlphaModel())

        self.settings.rebalance_portfolio_on_security_changes = False
        self.settings.rebalance_portfolio_on_insight_changes = False
        self.day = -1
        self.set_portfolio_construction(EqualWeightingPortfolioConstructionModel(self._rebalance_func))

        self.add_risk_management(TrailingStopRiskManagementModel())

        self.set_execution(ImmediateExecutionModel())

        self.set_warm_up(timedelta(7))

    def _etf_constituents_filter(self, constituents: List[ETFConstituentUniverse]) -> List[Symbol]:
        selected = sorted([c for c in constituents if c.weight],
                          key=lambda c: c.weight, reverse=True)[:200]
        return [c.symbol for c in selected]

    def _rebalance_func(self, time):
        if self.day != self.time.day and not self.is_warming_up and self.current_slice.quote_bars.count > 0:
            self.day = self.time.day
            return time
        return None

    def on_data(self, data):
        if not self.is_warming_up and not self.checked_symbols_from_previous_deployment:
            for security_holding in self.portfolio.values():
                if not security_holding.invested:
                    continue
                symbol = security_holding.symbol
                if not self.insights.has_active_insights(symbol, self.utc_time):
                    self.undesired_symbols_from_previous_deployment.append(symbol)
            self.checked_symbols_from_previous_deployment = True

        for symbol in self.undesired_symbols_from_previous_deployment:
            if self.is_market_open(symbol):
                self.liquidate(symbol, tag="Not backed up by current insights")
                self.undesired_symbols_from_previous_deployment.remove(symbol)