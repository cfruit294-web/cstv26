"""Jeton signé et temporaire donnant accès à la lecture HLS d'un live privé.

Les lives publics ne demandent aucun token (accès libre). Pour un live privé, le token propage le
droit d'accès (déjà vérifié une fois par CanAccessLiveStream côté détail) vers les requêtes de
segments faites par le lecteur (navigateur/hls.js), qui ne peuvent pas envoyer d'en-tête
Authorization sur chaque requête de manifest/segment. Même principe que videos.tokens.
"""
from django.core import signing

LIVE_HLS_TOKEN_SALT = 'live.hls_access'
LIVE_HLS_TOKEN_MAX_AGE_SECONDS = 6 * 3600


def generate_live_hls_token(stream_id):
    return signing.dumps({'stream_id': str(stream_id)}, salt=LIVE_HLS_TOKEN_SALT)


def verify_live_hls_token(token, stream_id):
    try:
        payload = signing.loads(token, salt=LIVE_HLS_TOKEN_SALT, max_age=LIVE_HLS_TOKEN_MAX_AGE_SECONDS)
    except signing.BadSignature:
        return False
    return payload.get('stream_id') == str(stream_id)
