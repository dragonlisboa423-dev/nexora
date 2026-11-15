"""Deterministic checks with explicit dimensions and roles; no model or network."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Mass(StrictArgs):
    value: Decimal = Field(ge=0, le=Decimal("1e12"), max_digits=24, decimal_places=12)
    unit: Literal["kg", "g"]

    def kg(self):
        return self.value if self.unit == "kg" else self.value / 1000


class LoadCheck(StrictArgs):
    masses: list[Mass] = Field(min_length=1, max_length=50)
    capacity: Mass


class Power(StrictArgs):
    value: Decimal = Field(ge=0, le=Decimal("1e9"), max_digits=24, decimal_places=12)
    unit: Literal["W", "kW"]


class EnergyCheck(StrictArgs):
    power: Power
    hours_per_day: Decimal = Field(ge=0, le=24, max_digits=14, decimal_places=8)
    days: Decimal = Field(gt=0, le=36600, max_digits=14, decimal_places=8)
    tariff_brl_per_kwh: Decimal = Field(ge=0, le=1000000, max_digits=14, decimal_places=8)


def check_load(arguments):
    body = LoadCheck.model_validate(arguments)
    total = sum((mass.kg() for mass in body.masses), Decimal(0))
    capacity = body.capacity.kg()
    excess = max(total - capacity, Decimal(0))
    return {
        "total_load": {"value": float(total), "unit": "kg"},
        "capacity": {"value": float(capacity), "unit": "kg", "role": "comparison_limit"},
        "excess": {"value": float(excess), "unit": "kg", "role": "excess_load_not_water_volume"},
        "within_stated_capacity": total <= capacity,
        "method": "decimal_mass_sum_and_comparison",
        "scope": "Cálculo das massas e limite informados; não verifica medições, distribuição de carga ou integridade do móvel.",
    }


def check_energy_cost(arguments):
    body = EnergyCheck.model_validate(arguments)
    kw = body.power.value / 1000 if body.power.unit == "W" else body.power.value
    energy = kw * body.hours_per_day * body.days
    cost = energy * body.tariff_brl_per_kwh
    return {
        "energy": {"value": float(energy), "unit": "kWh"},
        "cost": {"value": float(cost), "unit": "BRL"},
        "method": "decimal_power_times_duration_times_tariff",
        "scope": "Estimativa teórica para potência constante e tarifa informada; não mede consumo real nem inclui tributos adicionais.",
    }
