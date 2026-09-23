from datetime import date
from boa.core.module_specs import ModuleBlockSpec
from boa.modules.spec_tools import B, C, I, INFO, P, PATH, S, T, V


SPECS: dict[str, ModuleBlockSpec] = {}


def _add(*specs: ModuleBlockSpec) -> None:
    SPECS.update((spec.key, spec) for spec in specs)


# Date and time --------------------------------------------------------------
TODAY = date.today()
_add(
    S("datetime_now", "Date et heure actuelles", "Renvoie la date, l’heure ou la date complète actuelle.", "datetime",
      fields=(C("mode", "current_datetime", "current_date", "current_time", "timestamp"),),
      variants={
          "current_datetime": V((), (P("result", "date et heure", "datetime"),)),
          "current_date": V((), (P("result", "date", "date"),)),
          "current_time": V((), (P("result", "heure", "time"),)),
          "timestamp": V((), (P("result", "timestamp", "float"),)),
      }, imports=("datetime",)),
    S("datetime_create", "Créer une date ou une heure", "Construit une date, une heure ou une date complète.", "datetime",
      fields=(
          C("mode", "date", "time", "datetime"),
          I("year", TODAY.year, show_if=(("mode", ("date", "datetime")),), minimum=1, maximum=9999),
          I("month", TODAY.month, show_if=(("mode", ("date", "datetime")),), minimum=1, maximum=12),
          I("day", TODAY.day, show_if=(("mode", ("date", "datetime")),), minimum=1, maximum=31),
          I("hour", 0, show_if=(("mode", ("time", "datetime")),), maximum=23),
          I("minute", 0, show_if=(("mode", ("time", "datetime")),), maximum=59),
          I("second", 0, show_if=(("mode", ("time", "datetime")),), maximum=59),
      ),
      variants={
          "date": V((P("year", "année", "int"), P("month", "mois", "int"), P("day", "jour", "int")), (P("result", "date", "date"),)),
          "time": V((P("hour", "heure", "int"), P("minute", "minute", "int"), P("second", "seconde", "int")), (P("result", "heure", "time"),)),
          "datetime": V((P("year", "année", "int"), P("month", "mois", "int"), P("day", "jour", "int"), P("hour", "heure", "int"), P("minute", "minute", "int"), P("second", "seconde", "int")), (P("result", "date et heure", "datetime"),)),
      }, imports=("datetime",), selectable_inputs=True),
    S("datetime_parts", "Décomposer une date", "Extrait les différentes parties d’une date ou d’une heure.", "datetime",
      (P("value", "date / heure"),),
      (P("year", "année", "int"), P("month", "mois", "int"), P("day", "jour", "int"), P("hour", "heure", "int"), P("minute", "minute", "int"), P("second", "seconde", "int")),
      imports=("datetime",)),
    S("datetime_shift", "Décaler une date", "Ajoute ou retire une durée à une date.", "datetime",
      (P("value", "date / heure"), P("days", "jours", "float"), P("hours", "heures", "float"), P("minutes", "minutes", "float")),
      (P("result", "résultat"),), imports=("datetime",)),
    S("datetime_difference", "Différence entre deux dates", "Calcule la durée séparant deux dates.", "datetime",
      (P("start_value", "début"), P("end_value", "fin")),
      (P("duration", "durée", "timedelta"), P("days", "jours", "float"), P("seconds", "secondes", "float")), imports=("datetime",)),
    S("datetime_format", "Convertir date et texte", "Formate une date en texte ou analyse un texte comme date.", "datetime",
      fields=(C("mode", "date_to_text", "text_to_date"), T("date_format", "%d/%m/%Y %H:%M:%S", "info.datetime.format")),
      variants={
          "date_to_text": V((P("value", "date / heure"),), (P("result", "texte", "str"),)),
          "text_to_date": V((P("value", "texte", "str"),), (P("result", "date et heure", "datetime"),)),
      }, imports=("datetime",)),
    S("datetime_weekday", "Jour de la semaine", "Renvoie le numéro et le nom du jour de la semaine.", "datetime",
      (P("value", "date"),), (P("number", "numéro", "int"), P("name", "nom", "str")),
      fields=(INFO("weekday_help", "info.datetime.weekday"),), imports=("datetime",)),
)


