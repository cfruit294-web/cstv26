"""Client pour l'API CinetPay (https://cinetpay.com/) : initiation et vérification de paiement."""
import uuid

import requests
from django.conf import settings


class CinetPayError(Exception):
    """Levée lorsque CinetPay renvoie une erreur métier ou est injoignable."""


def generate_transaction_id():
    return f'SF{uuid.uuid4().hex[:20]}'


def _credentials():
    if not settings.CINETPAY_API_KEY or not settings.CINETPAY_SITE_ID:
        raise CinetPayError("CINETPAY_API_KEY / CINETPAY_SITE_ID ne sont pas configurées sur le serveur.")
    return {'apikey': settings.CINETPAY_API_KEY, 'site_id': settings.CINETPAY_SITE_ID}


def initiate_payment(*, transaction_id, amount, currency, description, customer_email, notify_url, return_url):
    """Crée une transaction CinetPay et retourne l'URL de paiement à présenter à l'utilisateur."""
    payload = {
        **_credentials(),
        'transaction_id': transaction_id,
        'amount': int(amount),
        'currency': currency,
        'description': description[:255],
        'notify_url': notify_url,
        'return_url': return_url,
        'channels': 'ALL',
        'customer_email': customer_email,
    }
    try:
        response = requests.post(settings.CINETPAY_INIT_URL, json=payload, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise CinetPayError(f'Impossible de contacter CinetPay : {exc}') from exc

    data = response.json()
    if data.get('code') != '201':
        raise CinetPayError(data.get('message', 'Erreur CinetPay inconnue.'))
    return data['data']


def check_payment_status(transaction_id):
    """Interroge CinetPay pour connaître le statut réel d'une transaction (source de vérité, pas le webhook seul)."""
    payload = {**_credentials(), 'transaction_id': transaction_id}
    try:
        response = requests.post(settings.CINETPAY_CHECK_URL, json=payload, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise CinetPayError(f'Impossible de contacter CinetPay : {exc}') from exc

    return response.json()


def extract_status(check_response):
    """Extrait le statut normalisé ('ACCEPTED' | 'REFUSED' | 'PENDING' | ...) d'une réponse de vérification."""
    return (check_response.get('data') or {}).get('status')
