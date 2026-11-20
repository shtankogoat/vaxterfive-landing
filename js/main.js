// marquee: duplicate items for seamless loop
const track=document.getElementById('track');{const s=track.innerHTML,n=track.children.length;let k=1;track.innerHTML=s;const w=()=>track.scrollWidth;const fill=()=>{const need=Math.max(innerWidth,screen.width||0)+200;const one=w()/(track.children.length/n)/1;let c=Math.max(1,Math.ceil(need/Math.max(1,one)));if(c!==k||track.children.length!==2*c*n){k=c;track.innerHTML=s.repeat(2*c);track.style.animationDuration=(40*c)+'s'}};fill();addEventListener('load',fill);addEventListener('resize',fill)}

// swatches (данные — js/swatches.js)
const swatches=window.SWATCHES||[];
const box=document.getElementById('swatches'),modal=document.getElementById('modal');
swatches.forEach(s=>{
  const b=document.createElement('button');b.className='sw';b.type='button';
  b.innerHTML='<div class="chip"></div><b></b><small></small>';b.querySelector('b').textContent=s.n;b.querySelector('small').textContent=s.t;
  b.onclick=()=>{document.getElementById('m-chip').style.background=s.c;
    document.getElementById('m-type').textContent=s.t;document.getElementById('m-title').textContent=s.n;
    document.getElementById('m-desc').textContent=s.d;modal.classList.add('open')};
  box.appendChild(b);
});
// swatch photos load only when the block approaches the viewport
const paint=()=>box.querySelectorAll('.chip').forEach((c,i)=>{c.style.background=swatches[i].c});
if('IntersectionObserver'in window){const so=new IntersectionObserver(es=>{if(es.some(x=>x.isIntersecting)){paint();so.disconnect()}},{rootMargin:'400px'});so.observe(box)}else paint();
const closeM=()=>modal.classList.remove('open');
document.getElementById('close').onclick=closeM;
modal.onclick=e=>{if(e.target===modal)closeM()};
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeM()});

// reveal on scroll
const io=new IntersectionObserver(es=>es.forEach(x=>{if(x.isIntersecting){x.target.classList.add('in');io.unobserve(x.target)}}),{threshold:.12});
document.querySelectorAll('.reveal').forEach(el=>io.observe(el));


// constructor: load CSS + JS lazily, near the viewport or on #k= / #constructor links
(()=>{const sec=document.getElementById('constructor');if(!sec)return;let started=false;
const go=()=>{if(started)return;started=true;const q=document.querySelector('meta[name="kc-assets"]');const [css,js]=(q?q.content:'/css/constructor.min.css|/js/constructor.min.js').split('|');
  const l=document.createElement('link');l.rel='stylesheet';l.href=css;
  const run=()=>{const sc=document.createElement('script');sc.src=js;sc.onload=()=>{sec.classList.add('kc-ready');if(location.hash==='#constructor')sec.scrollIntoView()};sc.onerror=()=>sec.classList.add('kc-ready');document.body.appendChild(sc)};
  l.onload=run;l.onerror=run;document.head.appendChild(l)};
const want=()=>/^#(k=|constructor)/.test(location.hash);
if(want())go();
addEventListener('hashchange',()=>{if(want())go()});
document.addEventListener('click',e=>{const a=e.target.closest&&e.target.closest('a[href$="#constructor"]');if(a)go()});
if('IntersectionObserver'in window){const o=new IntersectionObserver(es=>{if(es.some(x=>x.isIntersecting)){o.disconnect();go()}},{rootMargin:'600px'});o.observe(sec)}else go();
})();
