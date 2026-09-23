from boa.core.module_specs import ModuleBlockSpec
from boa.modules.spec_tools import B, C, I, INFO, P, PATH, S, T, V

RELATIVE = B("relative_to_project", False, "info.path.relative")


SPECS: dict[str, ModuleBlockSpec] = {}


def _add(*specs: ModuleBlockSpec) -> None:
    SPECS.update((spec.key, spec) for spec in specs)


# Archives and compression ---------------------------------------------------
ARCHIVE_FORMATS = ("zip", "tar", "tar_gz", "tar_bz2", "tar_xz")
_add(
    S("archive_create", "Créer une archive", "Regroupe un dossier ou une liste de chemins dans une archive.", "archive",
      fields=(C("mode", "folder", "path_list"), C("format", *ARCHIVE_FORMATS), PATH("source_path"), PATH("destination_path"), RELATIVE, C("existing", "refuse", "replace"), B("keep_root", True, "info.archive.root"), I("compression_level", 6)),
      variants={
          "folder": V((P("source", "dossier source", "str"), P("destination", "archive", "str")), (P("result", "archive", "str"),)),
          "path_list": V((P("source", "liste de chemins", "list"), P("destination", "archive", "str")), (P("result", "archive", "str"),)),
      }, flow=True, imports=("bz2", "lzma", "pathlib", "tarfile", "zipfile")),
    S("archive_extract", "Extraire une archive", "Extrait tout ou partie d’une archive dans un dossier.", "archive",
      fields=(C("format", "auto", *ARCHIVE_FORMATS), C("mode", "extract_all", "extract_selection"), PATH("archive_path"), PATH("destination_path", "folder"), RELATIVE, C("existing", "refuse", "replace", "ignore"), T("selection", "", show_if=(("mode", "extract_selection"),)), INFO("safety_help", "info.archive.safety")),
      variants={
          "extract_all": V((P("archive", "archive", "str"), P("destination", "destination", "str")), (P("folder", "dossier", "str"), P("items", "éléments", "list"))),
          "extract_selection": V((P("archive", "archive", "str"), P("destination", "destination", "str"), P("selection", "sélection", "list")), (P("folder", "dossier", "str"), P("items", "éléments", "list"))),
      }, flow=True, imports=("pathlib", "tarfile", "zipfile")),
    S("archive_inspect", "Inspecter une archive", "Liste le contenu et contrôle la validité d’une archive.", "archive",
      (P("archive", "archive", "str"),), (P("format", "format", "str"), P("items", "éléments", "list"), P("count", "nombre", "int"), P("compressed_size", "taille compressée", "int"), P("uncompressed_size", "taille décompressée", "int"), P("valid", "valide", "bool")),
      fields=(PATH("archive_path"), RELATIVE, B("verify_integrity", False, "info.archive.verify")), flow=True, imports=("pathlib", "tarfile", "zipfile")),
    S("archive_modify_zip", "Modifier une archive ZIP", "Ajoute, remplace, supprime ou renomme un élément ZIP.", "archive",
      fields=(C("mode", "add", "replace", "delete", "rename", info="info.archive.zip_only"), PATH("archive_path"), PATH("source_path"), RELATIVE),
      variants={
          "add": V((P("archive", "archive ZIP", "str"), P("source", "source", "str"), P("member", "nom interne", "str")), (P("result", "archive", "str"),)),
          "replace": V((P("archive", "archive ZIP", "str"), P("source", "source", "str"), P("member", "nom interne", "str")), (P("result", "archive", "str"),)),
          "delete": V((P("archive", "archive ZIP", "str"), P("member", "nom interne", "str")), (P("result", "archive", "str"),)),
          "rename": V((P("archive", "archive ZIP", "str"), P("member", "ancien nom", "str"), P("new_member", "nouveau nom", "str")), (P("result", "archive", "str"),)),
      }, flow=True, imports=("pathlib", "shutil", "tempfile", "zipfile")),
    S("compress_file", "Compresser un fichier", "Compresse ou décompresse un fichier unique.", "archive",
      (P("source", "source", "str"), P("destination", "destination", "str")), (P("result", "fichier", "str"),),
      fields=(C("mode", "compress", "decompress"), C("format", "gzip", "bzip2", "xz"), PATH("source_path"), PATH("destination_path"), RELATIVE, I("compression_level", 6)), flow=True, imports=("bz2", "gzip", "lzma", "pathlib", "shutil")),
    S("compress_bytes", "Compresser des octets", "Compresse ou décompresse des octets directement en mémoire.", "archive",
      (P("value", "octets", "bytes"),), (P("result", "octets", "bytes"),), fields=(C("mode", "compress", "decompress"), C("format", "zlib", "gzip", "bzip2", "lzma"), I("compression_level", 6)), imports=("bz2", "gzip", "lzma", "zlib")),
)
