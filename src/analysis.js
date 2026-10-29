import {Chess} from 'chess.js';
export const PLANS={
 'Missed forcing move':{habit:'Before every move, examine checks, captures and threats for both sides.',drill:'Replay these positions without the answer. Find a forcing candidate, calculate the reply, then compare the engine line.'},
 'Allowed a forcing reply':{habit:'Before committing, ask: what is my opponent’s strongest check, capture or threat?',drill:'From the position after your mistake, find the opponent’s forcing reply. Return to the original position and prevent it.'},
 'Other decision errors':{habit:'List two candidate moves and compare the opponent’s best reply to each.',drill:'Revisit these positions. Write two candidates and one concrete reply before revealing the engine recommendation.'}
};
export function parseGames(text){
 if(text.length>2_000_000)throw Error('PGN is too large. Import a smaller batch (up to 2 MB).');
 const chunks=text.trim().split(/(?=^\[Event\s)/m).filter(s=>s.trim());
 if(chunks.length>20)throw Error('Use at most 20 games per batch.');
 const seen=new Set();return chunks.map((pgn,i)=>{if((pgn.match(/^\[White\s/gm)||[]).length>1)throw Error('Separate games with Event headers in a PGN export.');const game=new Chess();try{game.loadPgn(pgn)}catch(e){throw Error(`Game ${i+1}: invalid or unsupported standard-chess PGN. ${e.message}`)}
 const h=game.getHeaders();if(!['1-0','0-1','1/2-1/2'].includes(h.Result))throw Error(`Game ${i+1}: import a completed game with a result.`);
 if(h.Variant&&!['standard','chess','normal'].includes(h.Variant.toLowerCase()))throw Error('Only standard chess is supported.');
 const moves=game.history({verbose:true});if(!moves.length)throw Error(`Game ${i+1} has no moves.`);const key=[h.White,h.Black,h.Date,h.Site,moves[0].before,...moves.map(m=>m.lan)].join('|');if(seen.has(key))throw Error('Duplicate game in batch. Remove the duplicate before analysis.');seen.add(key);return{pgn,headers:h,moves};});
}
export function playerColor(headers,username,side){if(side==='w'||side==='b')return side;const n=username.trim().toLowerCase();if(!n)throw Error('Enter your player name, or select White / Black.');if((headers.White||'').toLowerCase()===n)return'w';if((headers.Black||'').toLowerCase()===n)return'b';return null}
export function scoreValue(s){return s.mate!==undefined?(s.mate>0?10000-Math.min(99,s.mate):s.mate<0?-10000+Math.min(99,-s.mate):-10000):s.cp}
export function moveLoss(before,after){return Math.max(0,scoreValue(before)+scoreValue(after));}
export function uciMove(board,uci){if(!uci||uci==='(none)'||uci==='0000')return null;try{return board.move({from:uci.slice(0,2),to:uci.slice(2,4),promotion:uci[4]})}catch{return null}}
export function lineSAN(fen,line){const b=new Chess(fen),out=[];for(const u of line.slice(0,6)){const m=uciMove(b,u);if(!m)break;out.push(m.san)}return out.join(' ')}
export function phase(fen,ply){const b=new Chess(fen),pieces=b.board().flat().filter(Boolean);const heavy=pieces.filter(p=>['q','r','b','n'].includes(p.type));return heavy.length<=6?'Endgame':+fen.split(' ')[5]<=10?'Opening':'Middlegame'}
export function classify(fen,best,afterFen,reply){const b=new Chess(fen),m=uciMove(b,best);if(m&&(m.captured||m.san.includes('+')||m.san.includes('#')))return'Missed forcing move';const a=new Chess(afterFen),r=uciMove(a,reply);return r&&(r.captured||r.san.includes('+')||r.san.includes('#'))?'Allowed a forcing reply':'Other decision errors'}
export function aggregate(reports){const games=reports.length,moves=reports.reduce((s,r)=>s+r.reviewed,0),events=reports.flatMap(r=>r.events.map(e=>({...e,gameId:r.id,gameLabel:r.label})));const groups=Object.keys(PLANS).map(tag=>{const items=events.filter(e=>e.tag===tag);return{tag,count:items.length,games:new Set(items.map(e=>e.gameId)).size,impact:items.reduce((s,e)=>s+Math.min(e.loss,1000),0),items,...PLANS[tag]}}).filter(g=>g.count).sort((a,b)=>b.games-a.games||b.impact-a.impact||b.count-a.count);return{games,moves,events,groups}}
