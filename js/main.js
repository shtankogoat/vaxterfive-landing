// marquee: duplicate items for seamless loop
const track=document.getElementById('track');track.innerHTML+=track.innerHTML;

// swatches (данные — js/swatches.js)
const swatches=window.SWATCHES||[];
const box=document.getElementById('swatches'),modal=document.getElementById('modal');
swatches.forEach(s=>{
  const b=document.createElement('button');b.className='sw';
  b.innerHTML=`<div class="chip" style="background:${s.c}"></div><b>${s.n}</b><small>${s.t}</small>`;
  b.onclick=()=>{document.getElementById('m-chip').style.background=s.c;
    document.getElementById('m-type').textContent=s.t;document.getElementById('m-title').textContent=s.n;
    document.getElementById('m-desc').textContent=s.d;modal.classList.add('open')};
  box.appendChild(b);
});
const closeM=()=>modal.classList.remove('open');
document.getElementById('close').onclick=closeM;
modal.onclick=e=>{if(e.target===modal)closeM()};
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeM()});

// file name
document.getElementById('file').onchange=e=>{document.getElementById('file-name').textContent=e.target.files[0]?.name||'Перетащите или выберите файл'};

// form → Google Apps Script (см. google-script/README.md)
const FORM_ENDPOINT='PASTE_GOOGLE_SCRIPT_URL_HERE';
const form=document.getElementById('form'),okBox=document.getElementById('ok'),submitBtn=form.querySelector('[type=submit]');
const readFile=f=>new Promise((res,rej)=>{const r=new FileReader();r.onload=()=>res({name:f.name,type:f.type||'application/octet-stream',data:r.result.split(',')[1]});r.onerror=rej;r.readAsDataURL(f)});
form.onsubmit=async e=>{
  e.preventDefault();
  const data=Object.fromEntries(new FormData(form));
  delete data.attachment;
  const f=document.getElementById('file').files[0];
  if(f&&f.size>10*1024*1024){alert('Файл больше 10 МБ — пришлите его менеджеру в мессенджер.');return}
  submitBtn.disabled=true;submitBtn.textContent='ОТПРАВЛЯЕМ…';
  try{
    if(f)data.file=await readFile(f);
    data.page=location.href;
    // text/plain — чтобы браузер не делал preflight-запрос, который Apps Script не поддерживает
    const r=await fetch(FORM_ENDPOINT,{method:'POST',headers:{'Content-Type':'text/plain;charset=utf-8'},body:JSON.stringify(data)});
    const res=await r.json();
    if(!res.ok)throw new Error(res.error);
    okBox.textContent='Спасибо! Заявка отправлена — свяжемся с вами в ближайшее время.';okBox.style.background='';
    form.reset();document.getElementById('file-name').textContent='Перетащите или выберите файл';
  }catch(err){
    okBox.textContent='Не удалось отправить заявку. Позвоните нам: +7 (900) 474-30-00';okBox.style.background='#ffd2d2';
  }
  okBox.style.display='block';submitBtn.disabled=false;submitBtn.textContent='ОТПРАВИТЬ ЗАЯВКУ';
};

// reveal on scroll
const io=new IntersectionObserver(es=>es.forEach(x=>{if(x.isIntersecting){x.target.classList.add('in');io.unobserve(x.target)}}),{threshold:.12});
document.querySelectorAll('.reveal').forEach(el=>io.observe(el));

// top banner close (remember per visitor)
const topbar=document.getElementById('topbar');
try{if(localStorage.getItem('topbarClosed'))topbar.classList.add('hidden')}catch(e){}
document.getElementById('topbar-close').onclick=()=>{topbar.classList.add('hidden');try{localStorage.setItem('topbarClosed','1')}catch(e){}};
