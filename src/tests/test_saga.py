"""
Tests for store manager, choreographed saga
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""
import time
import json
from logger import Logger
import pytest
from store_manager import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health(client):
    result = client.get('/health-check')
    assert result.status_code == 200
    assert result.get_json() == {'status':'ok'}

def test_saga(client):
    """Smoke test for complete saga"""
    logger = Logger.get_instance("test")
    
    # 1. Run order saga
    product_data = {
        "user_id": 1,
        "items": [{"product_id": 2, "quantity": 1}, {"product_id": 3, "quantity": 2}]
    }
    response = client.post('/orders',
                          data=json.dumps(product_data),
                          content_type='application/json')
    
    assert response.status_code == 201, f"Failed to create order: {response.get_json()}"
    order_id = response.get_json()['order_id']
    assert order_id > 0
    logger.debug(f"Created order with ID: {order_id}")

    # Attente de 30s Pour attendre que la saga soit complétée.
    # (OrderCreated -> StockDecreased -> OutboxProcessor -> PaymentCreated -> SagaCompleted)
    max_wait = 30
    poll_interval = 2
    elapsed = 0
    payment_link = ''

    while elapsed < max_wait:
        time.sleep(poll_interval)
        elapsed += poll_interval

        response = client.get(f'/orders/{order_id}')
        assert response.status_code == 201, f"Failed to get order: {response.get_json()}"
        order_data = response.get_json()
        logger.debug(f"[{elapsed}s] order data: {order_data}")

        payment_link = order_data.get("payment_link", "")
        if "http" in payment_link:
            logger.debug(f"Saga completed after {elapsed}s")
            break

    # 2. Final assertions
    assert order_data["items"] is not None
    assert int(order_data["user_id"]) > 0
    assert float(order_data["total_amount"]) > 0
    assert "http" in payment_link, (
        f"payment_link never got set after {max_wait}s. Last value: '{payment_link}'. "
        f"Check that Kafka, the api-gateway, and payments-api containers are all running."
    )
    logger.debug(f"payment_link={payment_link}")