import math
import os
from datetime import datetime
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor, execute_values


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://eth_predictor:eth_predictor@localhost:5432/eth_predictor",
)


def _connect():
    return psycopg2.connect(DATABASE_URL)


def init_db() -> None:
    with _connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS prices (
                id BIGSERIAL PRIMARY KEY,
                coin VARCHAR(10) NOT NULL DEFAULT 'ETH',
                observed_at TIMESTAMPTZ NOT NULL,
                open DOUBLE PRECISION,
                high DOUBLE PRECISION,
                low DOUBLE PRECISION,
                price DOUBLE PRECISION NOT NULL,
                volume DOUBLE PRECISION
            );

            ALTER TABLE prices ADD COLUMN IF NOT EXISTS coin VARCHAR(10) NOT NULL DEFAULT 'ETH';
            ALTER TABLE prices ADD COLUMN IF NOT EXISTS open DOUBLE PRECISION;

            CREATE INDEX IF NOT EXISTS idx_prices_observed_at
                ON prices (observed_at DESC);
            CREATE INDEX IF NOT EXISTS idx_prices_coin_observed_at
                ON prices (coin, observed_at DESC);

            CREATE TABLE IF NOT EXISTS daily_candles (
                coin VARCHAR(10) NOT NULL DEFAULT 'ETH',
                candle_date TIMESTAMPTZ NOT NULL,
                open DOUBLE PRECISION NOT NULL,
                high DOUBLE PRECISION NOT NULL,
                low DOUBLE PRECISION NOT NULL,
                close DOUBLE PRECISION NOT NULL,
                volume DOUBLE PRECISION NOT NULL,
                PRIMARY KEY (coin, candle_date)
            );

            CREATE INDEX IF NOT EXISTS idx_daily_candles_coin_date
                ON daily_candles (coin, candle_date DESC);

            CREATE TABLE IF NOT EXISTS predictions (
                id BIGSERIAL PRIMARY KEY,
                coin VARCHAR(10) NOT NULL DEFAULT 'ETH',
                timeframe VARCHAR(10) NOT NULL,
                predicted_price DOUBLE PRECISION NOT NULL,
                current_price_at_prediction DOUBLE PRECISION NOT NULL,
                signal VARCHAR(32) NOT NULL,
                change_percent DOUBLE PRECISION,
                lower_bound DOUBLE PRECISION,
                upper_bound DOUBLE PRECISION,
                buy_score DOUBLE PRECISION DEFAULT 0,
                hold_score DOUBLE PRECISION DEFAULT 0,
                sell_score DOUBLE PRECISION DEFAULT 0,
                decision VARCHAR(16) DEFAULT 'HOLD',
                auto_buy_price DOUBLE PRECISION,
                auto_sell_price DOUBLE PRECISION,
                stop_loss_price DOUBLE PRECISION,
                last_open DOUBLE PRECISION,
                last_high DOUBLE PRECISION,
                last_low DOUBLE PRECISION,
                last_close DOUBLE PRECISION,
                last_volume DOUBLE PRECISION,
                created_at TIMESTAMPTZ NOT NULL,
                target_time TIMESTAMPTZ,
                model VARCHAR(100) NOT NULL,
                actual_price DOUBLE PRECISION,
                error_mape DOUBLE PRECISION,
                error_mae DOUBLE PRECISION,
                error_rmse DOUBLE PRECISION,
                direction_correct BOOLEAN,
                evaluated BOOLEAN NOT NULL DEFAULT FALSE,
                evaluated_at TIMESTAMPTZ
            );

            ALTER TABLE predictions ADD COLUMN IF NOT EXISTS coin VARCHAR(10) NOT NULL DEFAULT 'ETH';
            ALTER TABLE predictions ADD COLUMN IF NOT EXISTS buy_score DOUBLE PRECISION DEFAULT 0;
            ALTER TABLE predictions ADD COLUMN IF NOT EXISTS hold_score DOUBLE PRECISION DEFAULT 0;
            ALTER TABLE predictions ADD COLUMN IF NOT EXISTS sell_score DOUBLE PRECISION DEFAULT 0;
            ALTER TABLE predictions ADD COLUMN IF NOT EXISTS decision VARCHAR(16) DEFAULT 'HOLD';
            ALTER TABLE predictions ADD COLUMN IF NOT EXISTS auto_buy_price DOUBLE PRECISION;
            ALTER TABLE predictions ADD COLUMN IF NOT EXISTS auto_sell_price DOUBLE PRECISION;
            ALTER TABLE predictions ADD COLUMN IF NOT EXISTS stop_loss_price DOUBLE PRECISION;
            ALTER TABLE predictions ADD COLUMN IF NOT EXISTS last_open DOUBLE PRECISION;
            ALTER TABLE predictions ADD COLUMN IF NOT EXISTS last_high DOUBLE PRECISION;
            ALTER TABLE predictions ADD COLUMN IF NOT EXISTS last_low DOUBLE PRECISION;
            ALTER TABLE predictions ADD COLUMN IF NOT EXISTS last_close DOUBLE PRECISION;
            ALTER TABLE predictions ADD COLUMN IF NOT EXISTS last_volume DOUBLE PRECISION;
            ALTER TABLE predictions ADD COLUMN IF NOT EXISTS target_time TIMESTAMPTZ;
            ALTER TABLE predictions ADD COLUMN IF NOT EXISTS error_mae DOUBLE PRECISION;
            ALTER TABLE predictions ADD COLUMN IF NOT EXISTS error_rmse DOUBLE PRECISION;

            CREATE INDEX IF NOT EXISTS idx_predictions_timeframe_created
                ON predictions (timeframe, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_predictions_coin_tf_created
                ON predictions (coin, timeframe, created_at DESC);

            CREATE TABLE IF NOT EXISTS accuracy (
                coin VARCHAR(10) NOT NULL DEFAULT 'ETH',
                timeframe VARCHAR(10) NOT NULL,
                last_updated TIMESTAMPTZ NOT NULL,
                current_mape DOUBLE PRECISION NOT NULL,
                current_mae DOUBLE PRECISION NOT NULL DEFAULT 0,
                current_rmse DOUBLE PRECISION NOT NULL DEFAULT 0,
                current_accuracy DOUBLE PRECISION NOT NULL,
                samples INTEGER NOT NULL,
                PRIMARY KEY (coin, timeframe)
            );

            ALTER TABLE accuracy ADD COLUMN IF NOT EXISTS coin VARCHAR(10) NOT NULL DEFAULT 'ETH';
            ALTER TABLE accuracy ADD COLUMN IF NOT EXISTS current_mae DOUBLE PRECISION NOT NULL DEFAULT 0;
            ALTER TABLE accuracy ADD COLUMN IF NOT EXISTS current_rmse DOUBLE PRECISION NOT NULL DEFAULT 0;
            """
        )

        cursor.execute(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                      ON tc.constraint_name = kcu.constraint_name
                    WHERE tc.table_name = 'accuracy'
                      AND tc.constraint_type = 'PRIMARY KEY'
                    GROUP BY tc.constraint_name
                    HAVING COUNT(*) = 1
                ) THEN
                    ALTER TABLE accuracy DROP CONSTRAINT accuracy_pkey;
                    ALTER TABLE accuracy ADD PRIMARY KEY (coin, timeframe);
                END IF;
            EXCEPTION WHEN OTHERS THEN
                NULL;
            END $$;

            -- Bersihkan evaluasi lama yang berasal dari data jam-jaman (hourly), model Prophet lama pada 7d,
            -- atau yang tanggal targetnya masih di hari berjalan (>= hari ini WIB)
            DELETE FROM predictions
            WHERE model LIKE '%Prophet%'
               OR (
                  evaluated = TRUE
                  AND (
                      (target_time AT TIME ZONE 'Asia/Jakarta')::date >= (NOW() AT TIME ZONE 'Asia/Jakarta')::date
                      OR EXTRACT(HOUR FROM (target_time AT TIME ZONE 'Asia/Jakarta')) != 0
                      OR model IN ('LSTM (TensorFlow)', 'Hybrid LSTM + XGBoost (Residual Stacking)')
                  )
               );
            """
        )


def clear_evaluated_predictions(timeframe: str, coin: str = "ETH") -> None:
    with _connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            DELETE FROM predictions
            WHERE coin = %s AND timeframe = %s AND evaluated = TRUE
            """,
            (coin.upper(), timeframe),
        )


def upsert_daily_candles(candles: list[dict[str, Any]], coin: str = "ETH") -> None:
    if not candles:
        return
    coin_code = coin.upper()
    rows = []
    for c in candles:
        if any(c.get(k) is None for k in ("timestamp", "open", "high", "low", "close", "volume")):
            continue
        rows.append(
            (
                coin_code,
                c["timestamp"],
                float(c["open"]),
                float(c["high"]),
                float(c["low"]),
                float(c["close"]),
                float(c["volume"]),
            )
        )
    if not rows:
        return
    with _connect() as connection, connection.cursor() as cursor:
        execute_values(
            cursor,
            """
            INSERT INTO daily_candles (coin, candle_date, open, high, low, close, volume)
            VALUES %s
            ON CONFLICT (coin, candle_date) DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume
            """,
            rows,
        )


def get_daily_candles(coin: str = "ETH", limit: int = 60) -> list[dict[str, Any]]:
    with _connect() as connection, connection.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            """
            SELECT coin, candle_date AS timestamp, open, high, low, close, volume
            FROM daily_candles
            WHERE coin = %s
            ORDER BY candle_date DESC
            LIMIT %s
            """,
            (coin.upper(), limit),
        )
        return list(reversed(cursor.fetchall()))


def insert_price(data: dict[str, Any], coin: str = "ETH") -> None:
    coin_code = (data.get("coin") or coin or "ETH").upper()
    with _connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO prices (coin, observed_at, open, high, low, price, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                coin_code,
                data["timestamp"],
                data.get("open"),
                data.get("high"),
                data.get("low"),
                data["price"],
                data.get("volume"),
            ),
        )


def insert_prediction(data: dict[str, Any], coin: str = "ETH") -> None:
    coin_code = (data.get("coin") or coin or "ETH").upper()
    evaluated = bool(data.get("evaluated", False))
    with _connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO predictions (
                coin, timeframe, predicted_price, current_price_at_prediction,
                signal, change_percent, lower_bound, upper_bound,
                buy_score, hold_score, sell_score, decision,
                auto_buy_price, auto_sell_price, stop_loss_price,
                last_open, last_high, last_low, last_close, last_volume,
                created_at, target_time, model,
                actual_price, error_mape, error_mae, error_rmse,
                direction_correct, evaluated, evaluated_at
            )
            VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s
            )
            """,
            (
                coin_code,
                data["timeframe"],
                data["predicted_price"],
                data["current_price_at_prediction"],
                data["signal"],
                data.get("change_percent"),
                data.get("lower_bound"),
                data.get("upper_bound"),
                data.get("buy_score", 0.0),
                data.get("hold_score", 0.0),
                data.get("sell_score", 0.0),
                data.get("decision", "HOLD"),
                data.get("auto_buy_price"),
                data.get("auto_sell_price"),
                data.get("stop_loss_price"),
                data.get("last_open"),
                data.get("last_high"),
                data.get("last_low"),
                data.get("last_close", data["current_price_at_prediction"]),
                data.get("last_volume"),
                data["created_at"],
                data.get("target_time"),
                data["model"],
                data.get("actual_price"),
                data.get("error_mape"),
                data.get("error_mae"),
                data.get("error_rmse"),
                data.get("direction_correct"),
                evaluated,
                data.get("evaluated_at"),
            ),
        )


def latest_price(coin: str = "ETH") -> dict[str, Any] | None:
    with _connect() as connection, connection.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            """
            SELECT coin, open, price, high, low, volume, observed_at AS timestamp
            FROM prices
            WHERE coin = %s
            ORDER BY observed_at DESC
            LIMIT 1
            """,
            (coin.upper(),),
        )
        return cursor.fetchone()


def latest_prediction(timeframe: str, coin: str = "ETH") -> dict[str, Any] | None:
    with _connect() as connection, connection.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            """
            SELECT id, coin, timeframe, predicted_price, current_price_at_prediction,
                   signal, change_percent, lower_bound, upper_bound,
                   buy_score, hold_score, sell_score, decision,
                   auto_buy_price, auto_sell_price, stop_loss_price,
                   last_open, last_high, last_low, last_close, last_volume,
                   created_at, target_time, model,
                   actual_price, error_mape, error_mae, error_rmse, evaluated
            FROM predictions
            WHERE coin = %s AND timeframe = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (coin.upper(), timeframe),
        )
        return cursor.fetchone()


def prediction_history(
    timeframe: str,
    coin: str = "ETH",
    limit: int = 30,
    only_evaluated: bool = False,
) -> list[dict[str, Any]]:
    with _connect() as connection, connection.cursor(cursor_factory=RealDictCursor) as cursor:
        where_clause = "WHERE coin = %s AND timeframe = %s"
        if only_evaluated:
            # Hanya tampilkan data evaluasi yang hari targetnya SUDAH TUTUP (tanggal target < hari ini WIB)
            where_clause += (
                " AND evaluated = TRUE AND actual_price IS NOT NULL"
                " AND (target_time AT TIME ZONE 'Asia/Jakarta')::date < (NOW() AT TIME ZONE 'Asia/Jakarta')::date"
            )

        cursor.execute(
            f"""
            SELECT id, coin, timeframe, predicted_price, current_price_at_prediction,
                   signal, change_percent, lower_bound, upper_bound,
                   buy_score, hold_score, sell_score, decision,
                   auto_buy_price, auto_sell_price, stop_loss_price,
                   last_open, last_high, last_low, last_close, last_volume,
                   created_at, target_time, model,
                   actual_price, error_mape, error_mae, error_rmse,
                   error_mape AS error_rate, direction_correct, evaluated, evaluated_at
            FROM predictions
            {where_clause}
            ORDER BY COALESCE(target_time, created_at) DESC
            LIMIT %s
            """,
            (coin.upper(), timeframe, limit),
        )
        return list(reversed(cursor.fetchall()))


def evaluated_count(timeframe: str, coin: str = "ETH") -> int:
    with _connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM predictions
            WHERE coin = %s
              AND timeframe = %s
              AND evaluated = TRUE
              AND actual_price IS NOT NULL
              AND (target_time AT TIME ZONE 'Asia/Jakarta')::date < (NOW() AT TIME ZONE 'Asia/Jakarta')::date
            """,
            (coin.upper(), timeframe),
        )
        row = cursor.fetchone()
        return int(row[0]) if row else 0


def pending_predictions(timeframe: str, coin: str = "ETH", limit: int = 20) -> list[dict[str, Any]]:
    with _connect() as connection, connection.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            """
            SELECT id, coin, timeframe, predicted_price, current_price_at_prediction,
                   created_at, target_time
            FROM predictions
            WHERE coin = %s AND timeframe = %s AND evaluated = FALSE
            ORDER BY created_at ASC
            LIMIT %s
            """,
            (coin.upper(), timeframe, limit),
        )
        return cursor.fetchall()


def prices_between(start: datetime, end: datetime, coin: str = "ETH") -> list[dict[str, Any]]:
    with _connect() as connection, connection.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            """
            SELECT price, observed_at
            FROM prices
            WHERE coin = %s AND observed_at BETWEEN %s AND %s
            ORDER BY observed_at
            """,
            (coin.upper(), start, end),
        )
        return cursor.fetchall()


def mark_prediction_evaluated(
    prediction_id: int,
    actual_price: float,
    error_mape: float,
    error_mae: float,
    error_rmse: float,
    direction_correct: bool,
    evaluated_at: datetime,
) -> None:
    with _connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE predictions
            SET actual_price = %s,
                error_mape = %s,
                error_mae = %s,
                error_rmse = %s,
                direction_correct = %s,
                evaluated = TRUE,
                evaluated_at = %s
            WHERE id = %s
            """,
            (
                actual_price,
                error_mape,
                error_mae,
                error_rmse,
                direction_correct,
                evaluated_at,
                prediction_id,
            ),
        )


def upsert_accuracy(
    timeframe: str,
    updated_at: datetime,
    mape: float,
    mae: float,
    rmse: float,
    accuracy: float,
    samples: int,
    coin: str = "ETH",
) -> None:
    with _connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO accuracy
                (coin, timeframe, last_updated, current_mape, current_mae, current_rmse, current_accuracy, samples)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (coin, timeframe) DO UPDATE SET
                last_updated = EXCLUDED.last_updated,
                current_mape = EXCLUDED.current_mape,
                current_mae = EXCLUDED.current_mae,
                current_rmse = EXCLUDED.current_rmse,
                current_accuracy = EXCLUDED.current_accuracy,
                samples = EXCLUDED.samples
            """,
            (coin.upper(), timeframe, updated_at, mape, mae, rmse, accuracy, samples),
        )


def evaluation_metrics_summary(coin: str = "ETH") -> dict[str, Any]:
    coin_code = coin.upper()
    summary: dict[str, Any] = {}
    with _connect() as connection, connection.cursor(cursor_factory=RealDictCursor) as cursor:
        for tf in ("1d", "3d", "7d"):
            cursor.execute(
                """
                SELECT predicted_price, actual_price, current_price_at_prediction,
                       error_mape, error_mae, error_rmse, direction_correct, created_at
                FROM predictions
                WHERE coin = %s
                  AND timeframe = %s
                  AND evaluated = TRUE
                  AND actual_price IS NOT NULL
                  AND (target_time AT TIME ZONE 'Asia/Jakarta')::date < (NOW() AT TIME ZONE 'Asia/Jakarta')::date
                ORDER BY COALESCE(target_time, created_at) DESC
                LIMIT 50
                """,
                (coin_code, tf),
            )
            rows = cursor.fetchall()
            if not rows:
                summary[tf] = {
                    "timeframe": tf,
                    "coin": coin_code,
                    "rmse": 0.0,
                    "mae": 0.0,
                    "mape": 0.0,
                    "direction_accuracy": 0.0,
                    "samples": 0,
                }
                continue

            n = len(rows)
            sq_errors = []
            abs_errors = []
            pct_errors = []
            dir_hits = 0

            for r in rows:
                act = float(r["actual_price"])
                pred = float(r["predicted_price"])
                prev = float(r["current_price_at_prediction"] or act)
                diff = act - pred
                sq_errors.append(diff * diff)
                abs_errors.append(abs(diff))
                if act != 0:
                    pct_errors.append(abs(diff / act) * 100.0)
                if (act >= prev and pred >= prev) or (act < prev and pred < prev):
                    dir_hits += 1

            rmse = math.sqrt(sum(sq_errors) / n) if n else 0.0
            mae = sum(abs_errors) / n if n else 0.0
            mape = sum(pct_errors) / len(pct_errors) if pct_errors else 0.0
            dir_acc = (dir_hits / n) * 100.0 if n else 0.0

            summary[tf] = {
                "timeframe": tf,
                "coin": coin_code,
                "rmse": round(rmse, 2),
                "mae": round(mae, 2),
                "mape": round(mape, 4),
                "direction_accuracy": round(dir_acc, 2),
                "samples": n,
            }

    return summary
