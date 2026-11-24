// ==============================================================================
// HardTrack Solutions — Teste de Estresse / Descoberta de Gargalo (Etapa 3.3 · k6)
// Cenário: 40 VUs concentrados escrevendo simultaneamente no MESMO silo B2B
// Objetivo: Medir a degradação por contenção de lock + reescrita completa JSON (TinyDB)
// ==============================================================================

import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://127.0.0.1:8000';

export const options = {
  stages: [
    { duration: '5s', target: 40 },
    { duration: '15s', target: 40 },
    { duration: '3s', target: 0 },
  ],
  thresholds: {
    // Usamos o mesmo SLO de referência para evidenciar quando o gargalo o viola
    http_req_duration: ['p(95)<150'],
    http_req_failed: ['rate<0.01'],
  },
};

export function setup() {
  const res = http.post(
    `${BASE_URL}/tenants`,
    JSON.stringify({
      tenant_id: 'stress_single_b2b',
      nome: 'Mega Montadora Stress B2B',
      tipo: 'B2B_OFICINA',
      telegram_chat_id: '99119911',
    }),
    { headers: { 'Content-Type': 'application/json' } }
  );
  const body = res.json();
  return { tenant_id: body.tenant_id, token: body.access_token };
}

export default function (data) {
  const headers = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${data.token}`,
  };

  // Todos os 40 VUs competem pela mesma trava de arquivo (tenant_stress_single_b2b.json)
  const postRes = http.post(
    `${BASE_URL}/tenants/${data.tenant_id}/targets`,
    JSON.stringify({
      nome_componente: `Stress Item VU${__VU}-${__ITER}`,
      url: `mock://kabum.com.br/stress-${__VU}-${__ITER}?price=1999.00`,
      preco_alvo: 2100.0,
    }),
    { headers, tags: { endpoint: 'stress_post_same_silo' } }
  );

  check(postRes, { 'POST status 201': (r) => r.status === 201 });

  if (postRes.status === 201) {
    const id = postRes.json('id');
    http.del(`${BASE_URL}/tenants/${data.tenant_id}/targets/${id}`, null, {
      headers,
      tags: { endpoint: 'stress_del_same_silo' },
    });
  }

  sleep(0.05);
}

export function teardown(data) {
  http.del(`${BASE_URL}/tenants/${data.tenant_id}`, null, {
    headers: { Authorization: `Bearer ${data.token}` },
  });
}
