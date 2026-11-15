import hashlib
import json
import os
import subprocess
import sys

import pytest
from pydantic import ValidationError

from backend.core.policy import DATA, core_status, policy_prompt, read_bundle, retrieve_principles
from backend.core.quantities import EnergyCheck, LoadCheck, check_energy_cost, check_load


def test_supplied_seed_integrity_schema_and_traceable_scientific_retrieval():
    seed, manifest = read_bundle(DATA)
    assert manifest.sha256 == "8e9ff45e4d8a9793454d9c0442f3180c377314b79fcb443bbb811847b613fcbc"
    assert len(seed.regras_inviolaveis_propostas) == 12
    assert len(seed.avaliacao_e_testes_de_aceitacao.casos) == 16
    assert (
        seed.estado == "PROPOSTA_NAO_INSTALADA"
    )  # Source preserved, activation recorded separately.
    principles = retrieve_principles("amônia nitrito nitrato aquário ciclagem")
    assert any(p["id"] == "biologia_e_ecologia" for p in principles)
    assert all(p["sha256"] == manifest.sha256 and not p["verified_research"] for p in principles)
    assert retrieve_principles("xxxxxxxxxx") == []
    assert core_status()["sha256"] in policy_prompt()


def test_core_rejects_tampering_and_duplicate_rule_ids(tmp_path):
    for name in ("manifest.json", "SALY_CORE_MEMORY_v1.json"):
        (tmp_path / name).write_bytes((DATA / name).read_bytes())
    source = tmp_path / "SALY_CORE_MEMORY_v1.json"
    source.write_bytes(source.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="Integridade"):
        read_bundle(tmp_path)
    seed = json.loads(source.read_bytes())
    seed["regras_inviolaveis_propostas"][1]["id"] = seed["regras_inviolaveis_propostas"][0]["id"]
    source.write_text(json.dumps(seed), encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValidationError, match="IDs duplicados"):
        read_bundle(tmp_path)


def test_load_mass_conversion_and_capacity_roles_are_distinct():
    result = check_load(
        {
            "masses": [
                {"value": 11400, "unit": "g"},
                {"value": 2, "unit": "kg"},
                {"value": 1.5, "unit": "kg"},
                {"value": 800, "unit": "g"},
            ],
            "capacity": {"value": 12, "unit": "kg"},
        }
    )
    assert result["total_load"] == {"value": 15.7, "unit": "kg"}
    assert result["excess"]["value"] == 3.7
    assert result["excess"]["role"] == "excess_load_not_water_volume"
    assert result["capacity"]["role"] == "comparison_limit"
    assert not result["within_stated_capacity"]
    within = check_load(
        {"masses": [{"value": 1, "unit": "kg"}], "capacity": {"value": 2, "unit": "kg"}}
    )
    assert within["within_stated_capacity"] and within["excess"]["value"] == 0


@pytest.mark.parametrize(
    "value,unit", [(1, "L"), (1, "N"), (-1, "kg"), ("NaN", "kg"), ("Infinity", "kg")]
)
def test_load_rejects_invalid_dimensions_and_nonfinite_values(value, unit):
    with pytest.raises(ValidationError):
        LoadCheck.model_validate(
            {"masses": [{"value": value, "unit": unit}], "capacity": {"value": 12, "unit": "kg"}}
        )


@pytest.mark.parametrize("value,unit", [(3, "W"), (0.003, "kW")])
def test_energy_cost_normalizes_power_units(value, unit):
    result = check_energy_cost(
        {
            "power": {"value": value, "unit": unit},
            "hours_per_day": 24,
            "days": 30,
            "tariff_brl_per_kwh": 0.95,
        }
    )
    assert result["energy"] == {"value": 2.16, "unit": "kWh"}
    assert result["cost"] == {"value": 2.052, "unit": "BRL"}


@pytest.mark.parametrize(
    "change",
    [
        {"hours_per_day": 25},
        {"days": 0},
        {"tariff_brl_per_kwh": -1},
        {"power": {"value": 3, "unit": "kWh"}},
        {"execute": "shell"},
    ],
)
def test_energy_rejects_incompatible_units_bounds_and_extra_actions(change):
    with pytest.raises(ValidationError):
        EnergyCheck.model_validate(
            {
                "power": {"value": 3, "unit": "W"},
                "hours_per_day": 24,
                "days": 30,
                "tariff_brl_per_kwh": 0.95,
                **change,
            }
        )


def test_core_activation_and_authorized_memory_survive_separate_processes(tmp_path):
    environment = {
        **os.environ,
        "SALY_DATA_DIR": str(tmp_path),
        "SALY_DATABASE_URL": "sqlite:///" + str(tmp_path / "saly-v2.sqlite3"),
        "SALY_OWNER_PASSWORD_HASH": "",
    }
    initialize = """
from backend import storage as s
from backend.core import activate
from backend.services import Memory, memory_save
s.initialize()
activate()
memory_save(Memory(content='Preferência autorizada para teste de reinício', source='teste com consentimento'))
"""
    subprocess.run(
        [sys.executable, "-c", initialize], env=environment, check=True, capture_output=True
    )
    verify = """
import json
from backend import storage as s
from backend.core import activate
s.initialize()
before=s.setting('core_active')
epoch=s.setting('context_epoch')
activate()
print(json.dumps({'same_activation':before==s.setting('core_active'),'same_epoch':epoch==s.setting('context_epoch'),'activations':len(s.setting('core_activations')),'memories':s.all_records('memories')}))
"""
    result = subprocess.run(
        [sys.executable, "-c", verify], env=environment, check=True, capture_output=True, text=True
    )
    observed = json.loads(result.stdout)
    assert observed["same_activation"] and observed["same_epoch"] and observed["activations"] == 1
    assert len(observed["memories"]) == 1
    assert observed["memories"][0]["content"] == "Preferência autorizada para teste de reinício"
