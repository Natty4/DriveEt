# payments/verification.py
import requests
import re
import json
from dataclasses import dataclass
from typing import Optional, Dict, Any
from decimal import Decimal
import logging
logger = logging.getLogger(__name__)

@dataclass
class VerifyResult:
    success: bool
    payer_name: Optional[str] = None
    payer_account: Optional[str] = None
    receiver: Optional[str] = None
    receiver_account: Optional[str] = None
    amount: Optional[Decimal] = None
    date: Optional[str] = None
    reference: Optional[str] = None
    reason: Optional[str] = None
    error: Optional[str] = None
    
class PaymentVerifier:
    """
    Unified payment verification for multiple providers.
    """
   
    def __init__(self, mock_mode=False):
        self.mock_mode = mock_mode
       
    def verify_payment(self, method: str, reference: str) -> VerifyResult:
        """
        Verify payment using the appropriate provider.
       
        Args:
            method: Payment method (TELEBIRR, BOA, DASHEN)
            reference: Transaction reference number
           
        Returns:
            VerifyResult object with verification status
        """
        if self.mock_mode:
            return self._mock_verify(method, reference)
       
        method = method.upper()
       
        try:
            if method == 'TELEBIRR':
                return self._verify_telebirr(reference)
            elif method == 'BOA':
                return self._verify_boa(reference)
            elif method == 'DASHEN':
                return self._verify_dashen(reference)
            else:
                return VerifyResult(
                    success=False,
                    error=f"Unsupported payment method: {method}"
                )
        except Exception as e:
            logger.error(f"Payment verification error for {method}: {str(e)}")
            return VerifyResult(
                success=False,
                error=f"Verification failed: {str(e)}"
            )
   
    def _verify_telebirr(self, reference: str) -> VerifyResult:
        """Verify Telebirr transaction."""
        try:
            logger.info(f"📱 Verifying Telebirr transaction: {reference}")
           
            url = f"https://transactioninfo.ethiotelecom.et/receipt/{reference}"
            response = requests.get(url, timeout=30)
           
            if response.status_code != 200:
                return VerifyResult(
                    success=False,
                    error=f"Failed to fetch receipt (HTTP {response.status_code})"
                )
           
            html_content = response.text
           
            # Extract payer name
            payer_name_match = re.search(
                r'የከፋይ ስም/Payer Name.*?</td>\s*<td[^>]*>\s*([^<]+)',
                html_content,
                re.IGNORECASE | re.DOTALL
            )
            payer_name = payer_name_match.group(1).strip() if payer_name_match else None
           
            # Extract amount
            amount_match = re.search(
                r'የተከፈለው መጠን/Settled Amount.*?</td>\s*<td[^>]*>\s*([^<]+)',
                html_content,
                re.IGNORECASE | re.DOTALL
            )
            amount_str = amount_match.group(1).strip() if amount_match else None
           
            amount = None
            if amount_str:
                try:
                    amount_match = re.search(r'(\d+\.?\d*)', amount_str.replace(',', ''))
                    if amount_match:
                        amount = Decimal(amount_match.group(1))
                except:
                    pass
           
            if not payer_name or not amount:
                return VerifyResult(
                    success=False,
                    error="Could not extract payment details"
                )
           
            return VerifyResult(
                success=True,
                payer_name=payer_name,
                amount=amount,
                reference=reference
            )
           
        except requests.RequestException as e:
            logger.error(f"Telebirr HTTP error: {str(e)}")
            return VerifyResult(
                success=False,
                error=f"Network error: {str(e)}"
            )
   
    def _verify_boa(self, reference: str) -> VerifyResult:
        """Verify Bank of Abyssinia transaction."""
        try:
            logger.info(f"🏦 Verifying BoA transaction: {reference}")
           
            # Extract suffix if present
            suffix = ""
            if '-' in reference:
                reference, suffix = reference.split('-', 1)
                suffix = f"-{suffix}"
           
            api_url = f"https://cs.bankofabyssinia.com/api/onlineSlip/getDetails/?id={reference}{suffix}"
           
            response = requests.get(api_url, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Cache-Control': 'no-cache'
            })
           
            if response.status_code != 200:
                return VerifyResult(
                    success=False,
                    error=f"API returned HTTP {response.status_code}"
                )
           
            data = response.json()
           
            if not data.get('header', {}).get('status') == 'success':
                return VerifyResult(
                    success=False,
                    error=f"API error: {data.get('header', {}).get('message', 'Unknown error')}"
                )
           
            if not data.get('body') or len(data['body']) == 0:
                return VerifyResult(
                    success=False,
                    error="No transaction data found"
                )
           
            transaction = data['body'][0]
           
            # Parse amount
            amount_str = transaction.get('Transferred Amount', '')
            amount_match = re.search(r'[\d.]+', amount_str.replace(',', ''))
            amount = Decimal(amount_match.group(0)) if amount_match else None
           
            return VerifyResult(
                success=True,
                payer_name=transaction.get("Payer's Name"),
                payer_account=transaction.get('Source Account'),
                receiver=transaction.get('Source Account Name'),
                amount=amount,
                date=transaction.get('Transaction Date'),
                reference=transaction.get('Transaction Reference'),
                reason=transaction.get('Narrative')
            )
           
        except Exception as e:
            logger.error(f"BoA verification error: {str(e)}")
            return VerifyResult(success=False, error=str(e))
   
    def _verify_dashen(self, reference: str) -> VerifyResult:
        """Verify Dashen Bank transaction."""
        try:
            logger.info(f"🏦 Verifying Dashen transaction: {reference}")
           
            # This would need actual PDF parsing implementation
            # For now, return mock result
            return VerifyResult(
                success=False,
                error="Dashen verification not fully implemented"
            )
           
        except Exception as e:
            logger.error(f"Dashen verification error: {str(e)}")
            return VerifyResult(success=False, error=str(e))
   
    def _mock_verify(self, method: str, reference: str) -> VerifyResult:
        """Mock verification for development/testing."""
        logger.info(f"🔧 Mock verification for {method}: {reference}")
       
        import time
        time.sleep(0.5) # Simulate API delay
       
        # Generate deterministic mock result based on reference
        if reference.startswith('TEST'):
            return VerifyResult(
                success=True,
                payer_name=f"Test User {reference[-4:]}",
                payer_account="1234567890",
                receiver="Exam App",
                amount=Decimal('500.00'),
                date="2024-01-01 10:00:00",
                reference=reference,
                reason="Premium Subscription"
            )
        else:
            return VerifyResult(
                success=False,
                error="Mock payment not found"
            )