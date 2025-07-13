"""
Módulo de retry para requisições HTTP usando tenacity.
"""
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Decorator para retry em falhas de rede
retry_on_fail = retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(requests.exceptions.RequestException)
)