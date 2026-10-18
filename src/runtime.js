export async function guarded(action,{signal,worker,timeoutMs=90000,label='operation'}={}){
 if(signal?.aborted)throw new Error('Cancelled: '+label);
 let timer,onAbort,onError,onMessageError;
 const failure=new Promise((_,reject)=>{
  onAbort=()=>reject(new Error('Cancelled: '+label));
  onError=e=>reject(new Error(`${label}: Worker failed. ${e.message||'Check worker.js and the browser console.'}`));
  onMessageError=()=>reject(new Error(label+': Worker message error.'));
  signal?.addEventListener('abort',onAbort,{once:true});worker?.addEventListener('error',onError);worker?.addEventListener('messageerror',onMessageError);
  timer=setTimeout(()=>reject(new Error(`${label} timed out. Please reload the model and retry.`)),timeoutMs);
 });
 try{return await Promise.race([Promise.resolve().then(action),failure]);}
 finally{clearTimeout(timer);signal?.removeEventListener('abort',onAbort);worker?.removeEventListener('error',onError);worker?.removeEventListener('messageerror',onMessageError);}
}
export async function workerReady(worker,signal){let handler;try{return await guarded(()=>new Promise((resolve,reject)=>{handler=e=>{if(e.data?.type==='hidden-instructions-ready'){if(e.data.version!=='0.2.0')reject(Error('Worker version mismatch. Refresh the page.'));else resolve();}};worker.addEventListener('message',handler);}),{worker,signal,timeoutMs:15000,label:'Worker startup'});}finally{if(handler)worker.removeEventListener('message',handler);}}
