"""Jetons signés et temporaires donnant accès aux fichiers HLS d'une vidéo (manifest + segments).

Le contrôle d'accès réel (propriétaire/admin, visibilité publique) est fait une seule fois par
`CanAccessVideo` sur l'endpoint de détail ; le token signé propage ensuite ce droit vers les
requêtes de segments faites par le lecteur vidéo (navigateur/hls.js), qui ne peuvent pas envoyer
d'en-tête Authorization sur chaque requête de manifest/segment.
"""
from django.core import signing

HLS_TOKEN_SALT = 'videos.hls_access'
HLS_TOKEN_MAX_AGE_SECONDS = 6 * 3600


def generate_hls_token(video_id):
    return signing.dumps({'video_id': str(video_id)}, salt=HLS_TOKEN_SALT)


def verify_hls_token(token, video_id):
    try:
        payload = signing.loads(token, salt=HLS_TOKEN_SALT, max_age=HLS_TOKEN_MAX_AGE_SECONDS)
    except signing.BadSignature:
        return False
    return payload.get('video_id') == str(video_id)
