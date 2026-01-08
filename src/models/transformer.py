from __future__ import annotations
from dataclasses import dataclass

from models.line import Line
from models.bus import Bus


@dataclass
class TransformerMeta:
    sn_mva: float = 100.0
    hv_kv: float = 138.0
    lv_kv: float = 13.8

    # Ligação: "D", "Y", "Yg"
    conn_hv: str = "Y"
    conn_lv: str = "Y"

    # Aterramento/neutro (para curto assimétrico depois)
    grounded_hv: bool = False
    grounded_lv: bool = False
    xn_hv_pu: float = 0.0
    xn_lv_pu: float = 0.0


class Transformer(Line):
    """
    Transformador didático: VISÍVEL na UI e editável via popup.
    Por enquanto ele ainda é resolvido no PF como um 'ramo' (Line) com tap/impedância.
    """

    def __init__(
        self,
        *args,
        meta: TransformerMeta | None = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.meta: TransformerMeta = meta if meta is not None else TransformerMeta()

    @property
    def is_transformer(self) -> bool:
        return True

    @staticmethod
    def from_z(
        tap_bus_id: str | Bus,
        z_bus_id: str | Bus,
        z: complex,
        bc: float = 0.0,
        tap: float = 1.0,
        phase: float = 0.0,
        name: str | None = None,
        id: str | None = None,
        meta: TransformerMeta | None = None,
    ) -> "Transformer":
        # reaproveita a lógica do Line.from_z
        base_line = Line.from_z(
            tap_bus_id=tap_bus_id,
            z_bus_id=z_bus_id,
            z=z,
            bc=bc,
            tap=tap,
            phase=phase,
            name=name,
            id=id,
        )
        return Transformer(
            tap_bus_id=base_line.tap_bus_id,
            z_bus_id=base_line.z_bus_id,
            g=base_line.g,
            b=base_line.b,
            bc=base_line.bc,
            tap=base_line.tap,
            phase=base_line.phase,
            name=base_line.name,
            id=base_line.id,
            z1=base_line.z1,
            z2=base_line.z2,
            z0=base_line.z0,
            bc1=base_line.bc1,
            bc0=base_line.bc0,
            meta=meta,
        )

    @property
    def y0(self) -> complex:
        """
        Modelo simples de sequência zero para validação com Anafas:
        - Se qualquer lado for Δ -> NÃO há ligação de sequência zero entre as barras (ramo aberto).
        - Se não houver Δ, deixa como Line (por enquanto).
        """
        hv = self.meta.conn_hv
        lv = self.meta.conn_lv

        # delta bloqueia sequência zero entre barras
        if hv == "D" or lv == "D":
            return 0j

        # caso geral (sem delta): usa o mesmo comportamento de linha
        return super().y0
