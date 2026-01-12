import json
from typing import Tuple, cast

from maths.power_flow import PowerFlow
from models.bus import Bus, BusType
from models.line import Line
from models.transformer import Transformer, TransformerMeta
from storage.id_utils import norm_bus_id


def save_json_file(
    path: str, buses: list[Bus], lines: list[Line], positions: list[Tuple[float, float]]
) -> None:
    buses_json = list[dict[str, object]]()
    lines_json = list[dict[str, object]]()
    for index, bus in enumerate(buses):
        buses_json.append(
            {
                "id": bus.id,
                "name": bus.name,
                "v": bus.v,
                "o": bus.o,
                "p_load": bus.p_load,
                "q_load": bus.q_load,
                "p_gen": bus.p_gen,
                "q_gen": bus.q_gen,
                "q_min": bus.q_min,
                "q_max": bus.q_max,
                "type": bus.type.value,
                "v_rated": bus.v_rated,
                "b_shunt": bus.b_shunt,
                "g_shunt": bus.g_shunt,
                "position": positions[index],
            }
        )
        payload = {
            "id": line.id,
            "name": line.name,
            "b": line.b,
            "g": line.g,
            "bc": line.bc,
            "tap": line.tap,
            "tapBus": line.tap_bus_id,
            "zBus": line.z_bus_id,
        }

        if isinstance(line, Transformer):
            payload["kind"] = "transformer"
            payload["meta"] = {
                "sn_mva": line.meta.sn_mva,
                "hv_kv": line.meta.hv_kv,
                "lv_kv": line.meta.lv_kv,
                "conn_hv": line.meta.conn_hv,
                "conn_lv": line.meta.conn_lv,
                "grounded_hv": line.meta.grounded_hv,
                "grounded_lv": line.meta.grounded_lv,
                "xn_hv_pu": line.meta.xn_hv_pu,
                "xn_lv_pu": line.meta.xn_lv_pu,
            }
        else:
            payload["kind"] = "line"

        lines_json.append(payload)

    with open(path, "w") as f:
        json.dump({"buses": buses_json, "lines": lines_json}, f, indent=4)
    pass


def read_json_file(path: str) -> Tuple[list[Bus], list[Line], list[Tuple[float, float]]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    powerFlow = PowerFlow()
    positions: list[Tuple[float, float]] = []

    # -------------------------
    # 1) BUSES
    # -------------------------
    for busJson in data.get("buses", []):
        bid = norm_bus_id(busJson.get("id", busJson.get("number")))

        try:
            number = int(bid)
        except Exception:
            number = int(busJson.get("number", 0))

        bus = Bus(
            id=bid,
            number=number,
            name=busJson.get("name", bid),

            v=float(busJson.get("v", 1.0)),
            o=float(busJson.get("o", 0.0)),

            p_load=float(busJson.get("p_load", 0.0)),
            q_load=float(busJson.get("q_load", 0.0)),

            p_gen=float(busJson.get("p_gen", 0.0)),
            q_gen=float(busJson.get("q_gen", 0.0)),

            q_min=float(busJson.get("q_min", -1e9)),
            q_max=float(busJson.get("q_max", +1e9)),

            v_rated=float(busJson.get("v_rated", 0.0)),

            b_shunt=float(busJson.get("b_shunt", 0.0)),
            g_shunt=float(busJson.get("g_shunt", 0.0)),

            type=BusType(int(busJson.get("type", 0))),
        )

        # posição
        pos = busJson.get("position", None)
        if pos is not None:
            bus.position = pos
            try:
                positions.append((float(pos[0]), float(pos[1])))
            except Exception:
                positions.append((0.0, 0.0))
        else:
            positions.append((0.0, 0.0))

        powerFlow.add_bus(bus)

    # Conjunto de ids existentes (pra validação rápida)
    bus_ids = set(powerFlow.buses.keys())

    # -------------------------
    # 2) LINES / TRANSFORMERS
    # -------------------------
    for lineJson in data.get("lines", []):
        kind = lineJson.get("kind", None)

        tap_id = norm_bus_id(lineJson.get("tapBus"))
        z_id   = norm_bus_id(lineJson.get("zBus"))

        # valida antes de criar objeto
        if tap_id not in bus_ids or z_id not in bus_ids:
            raise ValueError(
                f"JSON inválido: conexão {lineJson.get('id','?')} referencia barra inexistente. "
                f"tapBus={tap_id!r} zBus={z_id!r}. "
                f"(buses carregadas={len(bus_ids)})"
            )

        # heurística didática: se tap != 1 e não vier kind, assume trafo
        is_trafo = (kind == "transformer") or (kind is None and float(lineJson.get("tap", 1.0)) != 1.0)

        if is_trafo:
            meta_json = lineJson.get("meta", {})
            if not isinstance(meta_json, dict):
                meta_json = {}

            meta = TransformerMeta(
                sn_mva=float(meta_json.get("sn_mva", 100.0)),
                hv_kv=float(meta_json.get("hv_kv", 138.0)),
                lv_kv=float(meta_json.get("lv_kv", 13.8)),
                conn_hv=str(meta_json.get("conn_hv", "Y")),
                conn_lv=str(meta_json.get("conn_lv", "Y")),
                grounded_hv=bool(meta_json.get("grounded_hv", False)),
                grounded_lv=bool(meta_json.get("grounded_lv", False)),
                xn_hv_pu=float(meta_json.get("xn_hv_pu", 0.0)),
                xn_lv_pu=float(meta_json.get("xn_lv_pu", 0.0)),
            )

            line = Transformer(
                id=lineJson.get("id", ""),
                name=lineJson.get("name", "Transformer"),
                b=float(lineJson.get("b", 0.0)),
                g=float(lineJson.get("g", 0.0)),
                bc=float(lineJson.get("bc", 0.0)),
                tap=float(lineJson.get("tap", 1.0)),
                tap_bus_id=tap_id,
                z_bus_id=z_id,
                meta=meta,
            )
        else:
            line = Line(
                id=lineJson.get("id", ""),
                name=lineJson.get("name", "Line"),
                b=float(lineJson.get("b", 0.0)),
                g=float(lineJson.get("g", 0.0)),
                bc=float(lineJson.get("bc", 0.0)),
                tap=float(lineJson.get("tap", 1.0)),
                tap_bus_id=tap_id,
                z_bus_id=z_id,
            )

        powerFlow.add_connection(line)

    return (
        list(powerFlow.buses.values()),
        list(powerFlow.connections.values()),
        positions,
    )

