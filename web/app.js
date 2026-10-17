'use strict';
const $ = id => document.getElementById(id);
const el = (tag, text, cls) => {
  const n = document.createElement(tag); n.textContent = text;
  if (cls) n.className = cls; return n;
};
const headers = () => ({'Content-Type': 'application/json', ...($('token').value ? {'Authorization': 'Bearer ' + $('token').value} : {})});
async function request(url, options = {}) {
  const response = await fetch(url, {...options, headers: headers()});
  const data = await response.json();
  if (!response.ok) throw Error(typeof data.detail === 'string' ? data.detail : 'Confira os valores dos filtros e da pergunta.');
  return data;
}
async function status() {
  try {
    const d = await request('/api/status');
    if (!d.ready) throw Error('Nenhuma coleção ativa. Execute a ingestão.');
    $('count').textContent = d.indexed.toLocaleString('pt-BR');
    $('read').textContent = d.preparation.read.toLocaleString('pt-BR');
    $('category').replaceChildren(new Option('Todas as categorias', ''));
    for (const category of d.categories) $('category').add(new Option(category.replaceAll('_', ' '), category));
    $('progress').textContent = d.selection === 'random_sample' ? 'Coleção de demonstração: amostra com seed 42.' : 'Coleção completa de avaliações com texto.';
  } catch (e) { $('progress').textContent = e.message; }
}
$('connect').onclick = status;
status();
document.querySelectorAll('.examples button').forEach(b => b.onclick = () => { $('question').value = b.textContent; $('question').focus(); });
$('ask').onsubmit = async event => {
  event.preventDefault();
  $('submit').disabled = true;
  $('progress').textContent = 'Recuperando evidências e verificando a resposta…';
  $('results').replaceChildren();
  const filters = {min_score: Number($('min').value), max_score: Number($('max').value), delivery: $('delivery').value};
  for (const [field, id] of [['purchase_start', 'purchase-start'], ['purchase_end', 'purchase-end'], ['review_start', 'start'], ['review_end', 'end'], ['category', 'category'], ['order_status', 'order-status']]) {
    if ($(id).value) filters[field] = $(id).value;
  }
  try {
    const d = await request('/api/query', {method: 'POST', body: JSON.stringify({question: $('question').value, filters, top_k: Number($('k').value), min_similarity: Number($('threshold').value)})});
    $('results').append(el('h2', d.message));
    for (const c of d.claims) {
      const row = el('div', '', 'claim'); row.append(el('div', c.text));
      row.append(el('small', c.evidence.map(x => '[' + x + ']').join(' ')));
      if (d.response_mode !== 'extractive') for (const q of c.quotes) row.append(el('p', '“' + q.text + '” [' + q.id + ']', 'muted'));
      $('results').append(row);
    }
    $('results').append(el('p', d.scope, 'notice'));
    if (d.evidence.length) $('results').append(el('h2', 'Evidências recuperadas'));
    for (const e of d.evidence) {
      const card = el('div', '', 'evidence');
      card.append(el('strong', '[' + e.citation + '] · Nota ' + e.score + '/5 · Similaridade ' + e.similarity.toFixed(3)));
      card.append(el('p', e.text));
      card.append(el('small', 'Avaliação: ' + e.review_id + ' | Pedido: ' + e.order_id));
      card.append(el('small', 'Compra: ' + (e.purchase_date || 'não informada') + ' | Avaliação: ' + (e.date || 'não informada')));
      const delivery = e.delay_days == null ? 'sem datas suficientes' : (e.delay_days > 0 ? e.delay_days + ' dias de atraso' : 'no prazo ou antecipada');
      card.append(el('small', 'Entrega: ' + delivery + ' | Situação: ' + (e.order_status || 'não informada')));
      card.append(el('small', 'Categorias do pedido: ' + (e.categories?.join(', ') || 'não informadas') + ' | Itens: ' + e.item_count));
      $('results').append(card);
    }
    const download = el('button', 'Baixar esta investigação (JSON)');
    download.onclick = () => {
      const a = document.createElement('a');
      const url = URL.createObjectURL(new Blob([JSON.stringify(d, null, 2)], {type: 'application/json'}));
      a.href = url; a.download = 'investigacao.json'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    };
    $('results').append(download);
    $('progress').textContent = d.elapsed_seconds + ' s · ' + d.evidence.length + ' evidências';
  } catch (e) { $('results').append(el('p', e.message, 'error')); $('progress').textContent = 'Consulta não concluída.'; }
  finally { $('submit').disabled = false; }
};
