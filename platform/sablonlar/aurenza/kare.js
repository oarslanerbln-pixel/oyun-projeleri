// Aurenza katmanı kareleri (2160x3840 PNG, saydam; final kısmı opak).
//   node kare.js <veri.json> <cikti_klasoru> <t1> [t2 ...]
//   node kare.js <veri.json> <cikti_klasoru> all <fps> <sure> [bas_indeks son_indeks]
// KANCA=A|B|C veri.json'daki kancaSecim'i geçersiz kılar.
const {chromium}=require('playwright'),path=require('path'),fs=require('fs');
(async()=>{const [veri,out,...ts]=process.argv.slice(2);fs.mkdirSync(out,{recursive:true});
 const V=JSON.parse(fs.readFileSync(veri,'utf8'));if(process.env.KANCA)V.kancaSecim=process.env.KANCA;
 const kok='file://'+path.resolve(path.dirname(veri))+'/';
 const b=await chromium.launch({args:['--allow-file-access-from-files']});const p=await b.newPage({viewport:{width:2160,height:3840},deviceScaleFactor:1});
 p.on('pageerror',e=>{console.error('HATA',e.message);process.exitCode=1});
 await p.addInitScript(([v,k])=>{window.VERI=v;window.VERI_KOK=k},[V,kok]);
 await p.goto('file://'+path.join(__dirname,'katman.html'));
 await p.evaluate(()=>Promise.all(['300 40px Int','500 40px Int','500 40px Cin','600 40px Cin','italic 500 40px Corm','italic 600 40px Corm','500 40px Corm','600 40px Corm'].map(f=>document.fonts.load(f,'ğşıİüöçÂâ’“ÄÖÜß'))));
 await p.evaluate(()=>window.hazir);
 let list=ts.map(t=>[t,t]);if(ts[0]==='all'){const f=+ts[1],d=+ts[2],s=+(ts[3]||0),e=+(ts[4]||Math.round(f*d));list=[];for(let i=s;i<e;i++)list.push([String(i/f),String(i).padStart(5,'0')]);}
 const el=await p.$('#c');
 for(const [t,n] of list){await p.evaluate(t=>draw(+t),t);await el.screenshot({path:path.join(out,n+'.png'),omitBackground:true});}
 await b.close();})();
