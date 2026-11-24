// ==============================================================================
// HardTrack Solutions — Teste de Carga no Cenário de Pico (Etapa 3.3 · k6)
// Cenário: 20 VUs simultâneos (15 tenants B2C + 5 tenants B2B) em promoção relâmpago
// Limiares (thresholds) idênticos aos declarados em docs/slo.md
// ==============================================================================

import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://127.0.0.1:8000';

export const options = {
  stages: [
    { duration: '5s', target: 20 },   // Ramp-up até o pico declarado (20 usuários simultâneos)
    { duration: '25s', target: 20 },  // Patamar sustentado de pico (Black Friday / Drop de GPU)
    { duration: '5s', target: 0 },    // Ramp-down
  ],
  thresholds: {
    http_req_duration: ['p(95)<150'],
    'http_req_duration{endpoint:post_target}': ['p(95)<150'],
    http_req_failed: ['rate<0.01'],
  },
};

export function setup() {
  const tenants = [];
  for (let i = 1; i <= 20; i++) {
    const isB2B = i > 15;
    const tenantId = isB2B ? `load_b2b_${i - 15}` : `load_b2c_${i}`;
    const payload = JSON.stringify({
      tenant_id: tenantId,
      nome: isB2B ? `Oficina Load B2B #${i - 15}` : `Gamer Load B2C #${i}`,
      tipo: isB2B ? 'B2B_OFICINA' : 'B2C_ENTUSIASTA',
      telegram_chat_id: `${700000 + i}`,
    });

    const res = http.post(`${BASE_URL}/tenants`, payload, {
      headers: { 'Content-Type': 'application/json' },
      tags: { endpoint: 'setup_tenant' },
    });

    const body = res.json();
    tenants.push({
      tenant_id: tenantId,
      token: body.access_token,
      tipo: body.tipo,
    });
  }
  return { tenants };
}

export default function (data) {
  // Cada VU representa um tenant distinto do pico (isolamento real por silo)
  const idx = (__VU - 1) % data.tenants.length;
  const tenant = data.tenants[idx];
  const headers = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${tenant.token}`,
  };

  // 1. Fluxo crítico: POST /tenants/{tenant_id}/targets
  const targetPayload = JSON.stringify({
    nome_componente: `GPU RTX 4070 Oferta VU${__VU}-IT${__ITER}`,
    url: `mock://kabum.com.br/gpu-${__VU}-${__ITER}?price=3699.00`,
    preco_alvo: 3800.0,
  });

  const postRes = http.post(
    `${BASE_URL}/tenants/${tenant.tenant_id}/targets`,
    targetPayload,
    { headers, tags: { endpoint: 'post_target' } }
  );

  check(postRes, {
    'POST /targets retorna 201': (r) => r.status === 201,
  });

  // 2. Consulta do painel: GET /tenants/{tenant_id}/targets
  const getRes = http.get(
    `${BASE_URL}/tenants/${tenant.tenant_id}/targets`,
    { headers, tags: { endpoint: 'get_targets' } }
  );

  check(getRes, {
    'GET /targets retorna 200': (r) => r.status === 200,
  });

  // 3. Limpeza do item criado para respeitar cota B2C (5 URLs) durante o teste contínuo
  if (postRes.status === 201) {
    const createdId = postRes.json('id');
    const delRes = http.del(
      `${BASE_URL}/tenants/${tenant.tenant_id}/targets/${createdId}`,
      null,
      { headers, tags: { endpoint: 'delete_target' } }
    );
    check(delRes, {
      'DELETE /targets/{id} retorna 200': (r) => r.status === 200,
    });
  }

  sleep(0.3);
}

export function teardown(data) {
  // Expurgo LGPD de todos os silos temporários criados no teste de carga
  for (const tenant of data.tenants) {
    http.del(`${BASE_URL}/tenants/${tenant.tenant_id}`, null, {
      headers: { Authorization: `Bearer ${tenant.token}` },
      tags: { endpoint: 'teardown_lgpd' },
    });
  }
}
