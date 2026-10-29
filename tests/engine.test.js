import test from 'node:test';import assert from 'node:assert/strict';import {spawn} from 'node:child_process';
test('real Stockfish WASM identifies mate in one via UCI',async()=>{
 const p=spawn(process.execPath,['node_modules/stockfish/bin/stockfish-18-lite-single.js']);
 try{await new Promise((resolve,reject)=>{let all='',sent=false;const timer=setTimeout(()=>reject(Error('Engine timeout')),20000);p.on('error',reject);p.stdout.on('data',chunk=>{all+=chunk;if(all.includes('uciok')&&!sent){sent=true;p.stdin.write('position startpos moves e2e4 e7e5 f1c4 b8c6 d1h5 g8f6\ngo depth 8\n')}if(all.includes('bestmove ')){clearTimeout(timer);try{assert.match(all,/score mate 1/);assert.match(all,/bestmove h5f7/);resolve()}catch(e){reject(e)}}});p.stdin.write('uci\n')})}finally{p.kill()}
});
