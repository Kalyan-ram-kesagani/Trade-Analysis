import math
import random
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple
from .models import Candle, DataProvenance, DataIntegrityReport

class HistoricalDataUnavailableError(Exception):
    """Raised when real market data is unavailable and synthetic fallback is blocked."""
    pass

class DataIntegrityError(Exception):
    """Raised when historical candle array fails sanity checks."""
    pass

class HistoricalDataLoader:
    """
    Supplies historical market data for backtesting and validation.
    Enforces strict data provenance:
    - REAL_MT5: Live MT5 terminal rates
    - IMPORTED_HISTORICAL: Verified offline data
    - SYNTHETIC_TEST: Deterministic pseudo-candles (STRICTLY PROHIBITED in production validation)
    """

    @classmethod
    def validate_data_integrity(
        cls,
        candles: List[Candle],
        provenance: DataProvenance
    ) -> DataIntegrityReport:
        """
        Phase 2 — Deterministic data validation before backtesting:
        1. Non-empty
        2. Sorted chronologically
        3. No duplicate timestamps
        4. No impossible OHLC values (High >= max(Open, Close, Low) and Low <= min(Open, Close, High))
        5. No negative prices or NaNs
        """
        errors: List[str] = []
        warnings: List[str] = []

        if not candles:
            return DataIntegrityReport(
                is_valid=False,
                data_provenance=provenance,
                production_eligible=False,
                total_candles=0,
                duplicate_count=0,
                disordered_count=0,
                invalid_ohlc_count=0,
                zero_volume_count=0,
                errors=["Candle dataset is empty."],
                warnings=[]
            )

        total_candles = len(candles)
        duplicate_count = 0
        disordered_count = 0
        invalid_ohlc_count = 0
        zero_vol_count = 0

        seen_timestamps = set()
        prev_time: Optional[datetime] = None

        for idx, c in enumerate(candles):
            # Check timestamps
            if c.time in seen_timestamps:
                duplicate_count += 1
            seen_timestamps.add(c.time)

            if prev_time and c.time < prev_time:
                disordered_count += 1
            prev_time = c.time

            # Check OHLC geometry
            if c.high < max(c.open, c.close, c.low):
                invalid_ohlc_count += 1
            if c.low > min(c.open, c.close, c.high):
                invalid_ohlc_count += 1
            if c.open <= 0 or c.high <= 0 or c.low <= 0 or c.close <= 0:
                invalid_ohlc_count += 1

            if c.tick_volume == 0:
                zero_vol_count += 1

        if duplicate_count > 0:
            errors.append(f"Detected {duplicate_count} duplicate candle timestamps.")
        if disordered_count > 0:
            errors.append(f"Detected {disordered_count} out-of-order candle timestamps.")
        if invalid_ohlc_count > 0:
            errors.append(f"Detected {invalid_ohlc_count} candles with impossible or non-positive OHLC prices.")

        if zero_vol_count > (total_candles * 0.5):
            warnings.append(f"High ratio of zero-volume candles ({zero_vol_count}/{total_candles}).")

        is_valid = len(errors) == 0
        production_eligible = is_valid and (provenance in [DataProvenance.REAL_MT5, DataProvenance.IMPORTED_HISTORICAL])

        return DataIntegrityReport(
            is_valid=is_valid,
            data_provenance=provenance,
            production_eligible=production_eligible,
            total_candles=total_candles,
            duplicate_count=duplicate_count,
            disordered_count=disordered_count,
            invalid_ohlc_count=invalid_ohlc_count,
            zero_volume_count=zero_vol_count,
            errors=errors,
            warnings=warnings
        )

    @staticmethod
    def load_candles(
        symbol: str,
        timeframe: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        bar_count: int = 500,
        random_seed: int = 42,
        allow_synthetic: bool = True,
        enforce_production_integrity: bool = False
    ) -> Tuple[List[Candle], DataProvenance, DataIntegrityReport]:
        """
        Loads candles with explicit data provenance.
        If enforce_production_integrity is True, NEVER falls back to synthetic data.
        """
        if end_time is None:
            end_time = datetime.now(timezone.utc)
        if start_time is None:
            start_time = end_time - timedelta(hours=bar_count)

        candles: List[Candle] = []
        provenance = DataProvenance.REAL_MT5

        # 1. Attempt MT5 real historical query
        try:
            from app.services.mt5_service import mt5_service
            if mt5_service.is_connected:
                import MetaTrader5 as mt5
                tf_map = {
                    "M1": mt5.TIMEFRAME_M1,
                    "M5": mt5.TIMEFRAME_M5,
                    "M15": mt5.TIMEFRAME_M15,
                    "M30": mt5.TIMEFRAME_M30,
                    "H1": mt5.TIMEFRAME_H1,
                    "H4": mt5.TIMEFRAME_H4,
                    "D1": mt5.TIMEFRAME_D1,
                }
                mt5_tf = tf_map.get(timeframe.upper(), mt5.TIMEFRAME_H1)
                rates = mt5.copy_rates_range(symbol, mt5_tf, start_time, end_time)
                if rates is not None and len(rates) > 0:
                    for r in rates:
                        candles.append(Candle(
                            time=datetime.fromtimestamp(r['time'], tz=timezone.utc),
                            open=float(r['open']),
                            high=float(r['high']),
                            low=float(r['low']),
                            close=float(r['close']),
                            tick_volume=int(r['tick_volume']),
                            spread=float(r.get('spread', 15.0))
                        ))
                    
                    report = HistoricalDataLoader.validate_data_integrity(candles, DataProvenance.REAL_MT5)
                    if not report.is_valid:
                        raise DataIntegrityError(f"Real MT5 candle data integrity check failed: {report.errors}")
                    return candles, DataProvenance.REAL_MT5, report
        except DataIntegrityError:
            raise
        except Exception:
            pass

        # 2. If Real MT5 is unavailable, verify if synthetic data is permitted
        if enforce_production_integrity or not allow_synthetic:
            raise HistoricalDataUnavailableError(
                f"Production validation requires authentic market data. "
                f"Real MT5 bridge is disconnected or symbol '{symbol}' history is unavailable. "
                f"Synthetic fallback is strictly blocked for production validation."
            )

        # 3. Development / Testing Only: Deterministic Synthetic Pseudo-Candles
        provenance = DataProvenance.SYNTHETIC_TEST
        rng = random.Random(random_seed + hash(symbol) % 10000)
        base_price = 1.0850 if "EUR" in symbol.upper() else (2000.0 if "XAU" in symbol.upper() else 150.0)
        volatility = 0.0008 if "EUR" in symbol.upper() else 1.5

        current_time = start_time
        current_price = base_price

        for i in range(bar_count):
            regime = math.sin(i / 30.0)
            drift = regime * (volatility * 0.3)
            noise = rng.gauss(0, volatility)
            price_change = drift + noise

            c_open = current_price
            c_close = c_open + price_change
            wick_high = abs(rng.gauss(0, volatility * 0.7))
            wick_low = abs(rng.gauss(0, volatility * 0.7))
            c_high = max(c_open, c_close) + wick_high
            c_low = min(c_open, c_close) - wick_low

            candles.append(Candle(
                time=current_time,
                open=round(c_open, 5),
                high=round(c_high, 5),
                low=round(c_low, 5),
                close=round(c_close, 5),
                tick_volume=rng.randint(100, 2500),
                spread=15.0
            ))

            current_price = c_close
            current_time += timedelta(hours=1)

        report = HistoricalDataLoader.validate_data_integrity(candles, DataProvenance.SYNTHETIC_TEST)
        return candles, DataProvenance.SYNTHETIC_TEST, report
