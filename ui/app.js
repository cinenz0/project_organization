(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const token = document.querySelector('meta[name="central-token"]').content;
  const els = ['shutdown','notice','source-name','source-path','central-name','central-path','choose-source','choose-central','review','review-title','summary','refresh','planned-rows','more','rename-note','retained','retained-summary','retained-list','retained-more','move-help','move','empty','empty-title','empty-text','empty-source','empty-refresh','result','result-title','result-summary','result-list','result-more','result-note','result-help','back-review','retry','another','loading','loading-title','loading-text','stage-review','stage-result'].reduce((a,id) => (a[id]=$(id),a),{});
  let snapshot = null, busy = false, shown = 75, retainedShown = 75, resultShown = 75, moving = false, connectionError = '';
  const mutators = ['shutdown','choose-source','choose-central','refresh','move','empty-source','empty-refresh','back-review','retry','another'];
  function plural(n, singular, pluralWord) { return `${n} ${n === 1 ? singular : pluralWord}`; }
  function size(value) { if (value === null || value === undefined) return ''; const units=['B','KB','MB','GB','TB']; let n=Number(value), i=0; while(n>=1024 && i<units.length-1){n/=1024;i++;} return `${new Intl.NumberFormat('pt-BR',{maximumFractionDigits:i?1:0}).format(n)} ${units[i]}`; }
  function clear(node) { node.replaceChildren(); }
  function setText(node, text) { node.textContent = text || ''; }
  function line(text, className) { const p=document.createElement('p'); p.textContent=text; if(className)p.className=className; return p; }
  async function api(path, data) { const options={headers:{'X-Central-Token':token}}; if(data !== undefined){options.method='POST';options.headers['Content-Type']='application/json';options.body=JSON.stringify(data);} const response=await fetch(path,options); let body; try { body=await response.json(); } catch { throw new Error('A resposta da aplicação não pôde ser lida. Atualize a prévia.'); } if(!response.ok) throw new Error(body.error || 'Não foi possível concluir a ação.'); return body; }
  function setBusy(value, message, isMoving=false) { busy=value; moving=value && isMoving; document.body.classList.toggle('busy',value); if(value) { mutators.forEach(id => els[id].disabled=true); showNotice(message); } else if(snapshot && snapshot.error) showNotice(snapshot.error,true); }
  function showNotice(message, error=false) { els.notice.hidden=!message; els.notice.className=`notice${error?' error':''}`; setText(els.notice,message); }
  function folder(kind, value) { setText(els[`${kind}-name`], value ? value.name : 'Nenhuma pasta selecionada'); setText(els[`${kind}-path`], value ? value.path : kind === 'source' ? 'Escolha a pasta que contém os arquivos.' : 'Escolha onde os arquivos serão organizados.'); }
  function opText(op) { return op.reason || op.error || (op.status === 'failed' ? 'Não foi possível incluir este arquivo na prévia.' : 'Permanece na origem.'); }
  function basename(path) { return String(path || '').split(/[\\/]/).pop() || '—'; }
  function renderRows(planned) { clear(els['planned-rows']); planned.slice(0,shown).forEach(op => { const row=document.createElement('tr'), file=document.createElement('td'), dest=document.createElement('td'), name=document.createElement('td'); const title=document.createElement('strong'), target=basename(op.destination); title.textContent=op.name || op.source; file.append(title); if(op.size !== null && op.size !== undefined) file.append(line(size(op.size),'file-size')); dest.textContent=op.category || '—'; name.textContent=target; if(target !== (op.name || '')) name.className='rename'; row.append(file,dest,name); els['planned-rows'].append(row); }); const renamed=planned.filter(op=>basename(op.destination)!==(op.name||'')); els['rename-note'].hidden=!renamed.length; setText(els['rename-note'],`${plural(renamed.length,'nome será ajustado','nomes serão ajustados')} para preservar os dois arquivos.`); els.more.hidden=planned.length<=shown; setText(els.more,`Mostrar mais ${Math.min(75, planned.length-shown)} de ${plural(planned.length,'arquivo','arquivos')}`); }
  function renderRetained(ops) { clear(els['retained-list']); els.retained.hidden=!ops.length; setText(els['retained-summary'],`${plural(ops.length,'item permanece','itens permanecem')} na origem`); ops.slice(0,retainedShown).forEach(op=>{const li=document.createElement('li'),b=document.createElement('strong');b.textContent=op.name||op.source;li.append(b,line(opText(op)));els['retained-list'].append(li);});els['retained-more'].hidden=ops.length<=retainedShown;setText(els['retained-more'],`Mostrar mais ${Math.min(75,ops.length-retainedShown)} de ${plural(ops.length,'item','itens')}`); }
  function renderResult(result) { const priority={failed:0,copied_source_retained:1,moved:2,skipped:3}; const operations=[...(result.operations||[])].sort((a,b)=>(priority[a.status]??4)-(priority[b.status]??4)), sum=result.summary||{}; const retryable=operations.filter(op=>op.status==='failed'&&op.retryable); const incomplete=operations.filter(op=>op.status==='failed'||op.status==='copied_source_retained'); const moved=sum.moved||0, copied=sum.copied||0; els.result.hidden=false; els.review.hidden=true; els.empty.hidden=true; els.loading.hidden=true; els['stage-review'].classList.remove('current');els['stage-result'].classList.add('current'); setText(els['result-title'], incomplete.length ? `${plural(moved,'arquivo movido','arquivos movidos')} · ${plural(incomplete.length,'pendência','pendências')}` : `${plural(moved,'arquivo movido','arquivos movidos')}`); setText(els['result-summary'], incomplete.length ? 'Confira os itens que permaneceram na origem.' : 'Os arquivos chegaram à pasta central.'); clear(els['result-list']); operations.slice(0,resultShown).forEach(op=>{const row=document.createElement('div'),status=document.createElement('span'),body=document.createElement('div'),name=document.createElement('strong'); row.className='result-row'; status.className='state'; name.textContent=op.name||op.source; let label='Preservado'; if(op.status==='moved'){label='Movido';status.classList.add('ok');} else if(op.status==='copied_source_retained'){label='Cópia na central';status.classList.add('warn');} else if(op.status==='failed'){label='Permaneceu na origem';status.classList.add('bad');} status.textContent=label; body.append(name); if(op.destination && op.status!=='failed') body.append(line(op.destination,'meta')); if(op.status==='copied_source_retained') body.append(line(`O original permanece em ${op.source}. Confira as duas cópias antes de organizar essa pasta novamente.`,'meta')); if(op.status==='failed') body.append(line(op.error||'Não foi possível mover este arquivo.','meta failed'),line(`Original em ${op.source}`,'meta')); if(op.status==='skipped') body.append(line(opText(op),'meta')); row.append(status,body);els['result-list'].append(row);}); els['result-more'].hidden=operations.length<=resultShown;setText(els['result-more'],`Mostrar mais ${Math.min(75,operations.length-resultShown)} de ${plural(operations.length,'item','itens')}`); const note=copied ? 'A cópia na central está pronta, mas o original permaneceu na origem. Confira as duas cópias antes de organizar essa pasta novamente.' : ''; els['result-note'].hidden=!note;setText(els['result-note'],note); setText(els['result-help'], retryable.length ? 'Tente novamente apenas os arquivos que podem ser recuperados.' : incomplete.length ? 'Os itens pendentes continuam na origem.' : ''); els.retry.hidden=!retryable.length;els.retry.disabled=busy||!retryable.length;setText(els.retry,`Tentar novamente (${retryable.length})`); }
  function render() {
    mutators.forEach(id => els[id].disabled=busy||!snapshot);
    els.move.disabled=true;
    els.retry.disabled=true;
    els.loading.hidden=!!snapshot;
    if(!snapshot) {
      showNotice(connectionError,!!connectionError);
      els.review.hidden=true; els.empty.hidden=true; els.result.hidden=true;
      setText(els['loading-title'],connectionError?'Não foi possível conectar':'Carregando…');
      setText(els['loading-text'],connectionError?'Atualize esta página ou reabra a aplicação.':'Lendo a configuração e preparando a prévia.');
      return;
    }
    folder('source',snapshot.source); folder('central',snapshot.central);
    if(!busy) showNotice(connectionError||snapshot.error,!!(connectionError||snapshot.error));
    if(snapshot.result){renderResult(snapshot.result);els.retry.disabled=busy||!!connectionError;return;}
    els['stage-review'].classList.add('current'); els['stage-result'].classList.remove('current');
    els.result.hidden=true;
    const planned=(snapshot.operations||[]).filter(op=>op.status==='planned');
    const retained=(snapshot.operations||[]).filter(op=>op.status!=='planned');
    const configured=snapshot.source&&snapshot.central;
    const empty=!configured||(!planned.length&&!retained.length);
    els.empty.hidden=!empty; els.review.hidden=empty;
    if(empty) {
      setText(els['empty-title'],snapshot.error&&configured?'Confira as pastas selecionadas':configured?'Esta pasta não tem arquivos para organizar':'Escolha as pastas para começar');
      setText(els['empty-text'],configured?'Escolha outra pasta de origem ou atualize a prévia.':'A prévia será criada automaticamente depois da escolha.');
      setText(els['empty-source'],!snapshot.central&&snapshot.source?'Escolher pasta central':'Escolher pasta de origem');
      els['empty-refresh'].hidden=!configured;
      return;
    }
    setText(els['review-title'],planned.length?plural(planned.length,'arquivo para mover','arquivos para mover'):'Nenhum arquivo será movido');
    const errors=(snapshot.summary||{}).errors||0;
    setText(els.summary,errors?plural(errors,'arquivo precisa de atenção','arquivos precisam de atenção'):'');
    renderRows(planned); renderRetained(retained);
    const available=planned.length>0&&!!snapshot.preview_id&&!connectionError;
    els.move.disabled=busy||!available;
    setText(els.move,`Mover ${plural(planned.length,'arquivo','arquivos')}`);
    setText(els['move-help'],snapshot.error?'A prévia mudou. Confira os destinos antes de clicar em mover.':available?'Os arquivos movidos sairão da pasta de origem.':'Não há arquivos prontos para mover.');
  }
  async function reconcile(message) { try { snapshot=await api('/api/state');connectionError='';render();showNotice(message||snapshot.error||'Confira o resultado antes de continuar.',true); } catch { connectionError='A conexão foi perdida. Reabra a aplicação para conferir os arquivos.';showNotice(connectionError,true); } }
  async function act(path,data,label,isMove=false) { if(busy)return;let failure='';setBusy(true,label,isMove);try{snapshot=await api(path,data);connectionError='';shown=75;retainedShown=75;resultShown=75;render();}catch(error){failure=error.message;await reconcile(failure);}finally{setBusy(false);render();if(failure)showNotice(connectionError||failure,true);} }
  els['choose-source'].onclick=()=>act('/api/choose-folder',{kind:'source'},'Escolha a pasta na janela do Windows');els['choose-central'].onclick=()=>act('/api/choose-folder',{kind:'central'},'Escolha a pasta na janela do Windows');els['empty-source'].onclick=els['choose-source'].onclick;els.refresh.onclick=()=>act('/api/refresh',{},'Atualizando a prévia…');els['back-review'].onclick=()=>act('/api/refresh',{},'Voltando à revisão…');els.another.onclick=els['choose-source'].onclick;els.move.onclick=()=>act('/api/move',{preview_id:snapshot.preview_id},'Movendo arquivos… aguarde',true);els.retry.onclick=()=>act('/api/retry',{},'Tentando mover os arquivos pendentes…',true);els.more.onclick=()=>{shown+=75;render();};els.shutdown.onclick=async()=>{if(busy)return;setBusy(true,'Encerrando a aplicação…');try{await api('/api/shutdown',{});document.body.classList.add('stopped');showNotice('A aplicação foi encerrada. Esta janela pode ser fechada.');}catch(error){setBusy(false);render();showNotice(error.message,true);}};
  els['empty-source'].onclick=()=>act('/api/choose-folder',{kind:snapshot?.source&&!snapshot?.central?'central':'source'},'Escolha a pasta na janela do Windows');
  els['empty-refresh'].onclick=els.refresh.onclick;
  els['retained-more'].onclick=()=>{retainedShown+=75;render();};
  els['result-more'].onclick=()=>{resultShown+=75;render();};
  addEventListener('beforeunload',event=>{if(moving){event.preventDefault();event.returnValue='';}});
  (async()=>{setBusy(true,'Carregando…');render();try{snapshot=await api('/api/state');}catch(error){connectionError=error.message;}finally{setBusy(false);render();}})();
})();
