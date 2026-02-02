from django.contrib.admin.sites import login_not_required
from django.http import Http404
from django.shortcuts import redirect

from apps.private.auths.models import QRCode, QRCodeScan
from apps.public.reviews.utils import get_etablissement_by_identifier
from starshield.logger import logger


@login_not_required
def qr_code_redirect_view(request, identifier=None, short_code=None):
    """Handle QR code scan and redirect to target based on routing."""
    etablissement = get_etablissement_by_identifier(identifier)

    if not short_code:
        logger.warning(f"QR code redirect called without short_code for etablissement {etablissement.id}")
        raise Http404()

    try:
        qr_code = QRCode.objects.get(short_code=short_code, etablissement=etablissement)
    except QRCode.DoesNotExist as err:
        logger.warning(f"QR code not found: short_code={short_code}, etablissement={etablissement.id}")
        raise Http404() from err

    # Track the scan
    try:
        QRCodeScan.objects.create(qr_code=qr_code)
    except Exception as e:
        logger.debug(f"Could not create QRCodeScan record: {e}")

    # Redirect to target based on routing
    target_url = qr_code.get_target_url(identifier)
    return redirect(target_url)
