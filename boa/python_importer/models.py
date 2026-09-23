from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ConversionReport:
    blocks: int = 0
    functions: int = 0
    classes: int = 0
    imports: int = 0
    native_blocks: int = 0
    structured_blocks: int = 0
    warnings: list[str] = field(default_factory=list)

    def message(self) -> str:
        lines = [
            f"{self.blocks} bloc(s) créé(s)",
            f"{self.native_blocks} bloc(s) Boa natif(s)",
            f"{self.functions} fonction(s) DEF créée(s)",
            f"{self.classes} classe(s) créée(s)",
            f"{self.imports} import(s) déplacé(s) dans les volets Imports",
            f"{self.structured_blocks} bloc(s) Python structuré(s)",
            "0 bloc Code Python libre (CPL)",
        ]
        if self.warnings:
            lines.extend(["", "Avertissements :", *[f"- {warning}" for warning in self.warnings]])
        return "\n".join(lines)


@dataclass(slots=True)
class ConversionResult:
    graph: dict
    functions: dict[str, dict]
    classes: dict[str, dict]
    imports: list[dict]
    variables: list[dict]
    report: ConversionReport
