"""Accès aux fichiers média indépendant du backend de stockage (disque local ou S3-compatible).

Le transcodage (ffmpeg) a besoin de vrais fichiers sur disque : le worker télécharge la source dans
un dossier temporaire, y produit HLS + miniature, puis pousse le résultat vers le stockage par
défaut. Avec FileSystemStorage, ça revient à copier dans MEDIA_ROOT ; avec S3, ça permet au web et
au worker de tourner sur des machines différentes sans disque partagé.
"""
import posixpath
import shutil
from contextlib import contextmanager
from pathlib import Path

from django.core.files import File
from django.core.files.storage import FileSystemStorage, default_storage
from django.http import Http404


def is_local_storage(storage=None):
    """True si le stockage expose de vrais chemins disque (FileSystemStorage), False pour S3 & co."""
    # isinstance plutôt que « path() lève-t-il NotImplementedError ? » : certains backends sans
    # disque (ex: InMemoryStorage) implémentent quand même path(). Passe à travers le LazyObject
    # default_storage (il proxifie __class__).
    return isinstance(storage or default_storage, FileSystemStorage)


def safe_media_name(prefix, relative_path):
    """Construit `prefix/relative_path` en refusant toute sortie du préfixe (`..`, chemin absolu).

    Version « clé de stockage » de core.media_access.resolve_within : fonctionne aussi pour S3, où
    il n'y a pas de chemin disque à résoudre.
    """
    if not relative_path or '\\' in relative_path or '\x00' in relative_path:
        raise Http404
    normalized = posixpath.normpath(relative_path)
    if normalized in ('.', '..') or normalized.startswith(('/', '../')):
        raise Http404
    return f'{prefix.rstrip("/")}/{normalized}'


@contextmanager
def local_copy(field_file, workdir):
    """Donne un chemin disque lisible par ffmpeg pour un FieldFile, quel que soit le stockage.

    Stockage local : renvoie directement le fichier (pas de copie inutile d'une grosse vidéo).
    Stockage distant : le télécharge par morceaux dans `workdir` (supprimé par l'appelant).
    """
    storage = field_file.storage
    if is_local_storage(storage):
        yield Path(field_file.path)
        return

    target = Path(workdir) / f'source{Path(field_file.name).suffix}'
    with storage.open(field_file.name, 'rb') as src, open(target, 'wb') as dst:
        shutil.copyfileobj(src, dst, length=8 * 1024 * 1024)
    yield target


def delete_prefix(prefix, storage=None):
    """Supprime récursivement tous les fichiers sous `prefix` (no-op si rien n'existe)."""
    storage = storage or default_storage
    try:
        directories, files = storage.listdir(prefix)
    except FileNotFoundError:
        return
    for name in files:
        storage.delete(f'{prefix}/{name}')
    for name in directories:
        delete_prefix(f'{prefix}/{name}', storage)


def upload_file(local_path, name, storage=None):
    """Écrit `local_path` sous le nom exact `name`, en écrasant l'éventuelle version précédente.

    Les backends renomment silencieusement en cas de collision (suffixe aléatoire) : on supprime
    d'abord, puis on vérifie que le nom obtenu est bien celui attendu, car les manifests HLS
    référencent les fichiers par leur nom exact.
    """
    storage = storage or default_storage
    storage.delete(name)
    with open(local_path, 'rb') as fh:
        saved_name = storage.save(name, File(fh))
    if saved_name != name:
        raise OSError(f'Stockage : fichier enregistré sous « {saved_name} » au lieu de « {name} ».')
    return saved_name


def upload_directory(local_dir, prefix, storage=None):
    """Remplace le contenu de `prefix` par celui de `local_dir` (arborescence conservée)."""
    storage = storage or default_storage
    delete_prefix(prefix, storage)
    local_dir = Path(local_dir)
    if not local_dir.is_dir():
        return
    for path in sorted(local_dir.rglob('*')):
        if path.is_file():
            upload_file(path, f'{prefix}/{path.relative_to(local_dir).as_posix()}', storage)
