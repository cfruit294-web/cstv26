"""Jeton signé et temporaire donnant accès au téléchargement d'un fichier numérique acheté.

Permet à OrderDigitalDownloadView (authentifiée par JWT) de déléguer la requête de téléchargement
elle-même à une simple navigation/lien direct, sans exiger que le navigateur renvoie l'en-tête
Authorization sur cette seconde requête.
"""
from django.core import signing

DOWNLOAD_TOKEN_SALT = 'orders.digital_download'
DOWNLOAD_TOKEN_MAX_AGE_SECONDS = 3600


def generate_download_token(order_id, product_id):
    return signing.dumps({'order_id': str(order_id), 'product_id': str(product_id)}, salt=DOWNLOAD_TOKEN_SALT)


def verify_download_token(token):
    try:
        return signing.loads(token, salt=DOWNLOAD_TOKEN_SALT, max_age=DOWNLOAD_TOKEN_MAX_AGE_SECONDS)
    except signing.BadSignature:
        return None
