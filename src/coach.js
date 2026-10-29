import {Chess} from 'chess.js';
import {uciMove,lineSAN} from './analysis.js';
const NAMES={p:'pawn',n:'knight',b:'bishop',r:'rook',q:'queen',k:'king'};
// Conventional material counts describe a short line, not its engine evaluation.
const VALUES={p:1,n:3,b:3,r:5,q:9,k:0};
const side=c=>c==='w'?'White':'Black';
const balance=(b,c)=>b.board().flat().filter(Boolean).reduce((s,p)=>s+(p.color===c?1:-1)*VALUES[p.type],0);
function moveDescription(m){return m.captured?`${NAMES[m.piece]} from ${m.from} captures the ${NAMES[m.captured]} on ${m.to}`:`${NAMES[m.piece]} moves from ${m.from} to ${m.to}`}
function pressure(b,m){const targets=b.board().flat().filter(p=>p&&p.color!==m.color&&p.type!=='k'&&VALUES[p.type]>VALUES[m.piece]&&b.attackers(p.square,m.color).includes(m.to)).sort((a,b)=>VALUES[b.type]-VALUES[a.type]);return targets.length?`Your ${NAMES[m.piece]} on ${m.to} attacks the ${NAMES[targets[0].type]} on ${targets[0].square}.`:''}
export function explainEvent(e){
 const unavailable={valid:false,title:'This example needs reanalysis',summary:'The saved moves could not be verified against the board. Reanalyze the game to get an explanation.',pattern:'Unverified saved example',fix:'Reanalyze this game before drawing conclusions.',practice:'Reanalyze this game.',why:[],better:[],played:e.played||'',best:'',line:'',replyLine:'',views:{}};
 let original;try{original=new Chess(e.fen)}catch{return unavailable}
 const actual=new Chess(e.fen),played=uciMove(actual,e.playedUci)||(()=>{try{return actual.move(e.played)}catch{return null}})();
 const alternative=new Chess(e.fen),best=uciMove(alternative,e.best);
 if(!played||!best||(e.afterFen&&actual.fen()!==e.afterFen))return unavailable;
 const afterPlayed=actual.fen(),afterBest=alternative.fen(),reply=uciMove(actual,e.reply),replyFen=reply?actual.fen():null;
 const replyText=reply?reply.san:'',line=lineSAN(e.fen,e.pv||[e.best]);
 const isActualReply=Boolean(reply&&e.nextPlayedUci===e.reply);
 const first=`On move ${e.moveNumber||original.moveNumber()+'.'}, you played ${played.san}.`;
 const why=[],better=[`The engine recommends ${best.san}: your ${moveDescription(best)}.`];
 let pattern,title,summary,fix,practice;
 if(reply&&actual.isCheckmate()){
  pattern='Immediate mate threats';title='You allowed checkmate on the next move';summary=`${first} ${side(reply.color)} ${isActualReply?'answered':'could reply'} ${reply.san}, which is checkmate.`;
  const p=pressure(new Chess(afterPlayed),played);if(p)why.push(p);
  why.push(`${reply.san} delivers checkmate: your king is in check and has no legal escape, capture or block.`);
  if(reply.captured&&reply.piece!=='k'){
   const supporters=actual.attackers(reply.to,reply.color).filter(s=>s!==reply.to).map(s=>({square:s,piece:actual.get(s)})).filter(x=>x.piece);
   if(supporters.length)why.push(`${side(reply.color)}’s ${supporters.map(x=>`${NAMES[x.piece.type]} on ${x.square}`).join(' and ')} ${supporters.length===1?'covers':'cover'} ${reply.to}, so your king cannot capture the ${NAMES[reply.piece]} there.`);
  }
  fix='Before choosing your move, look for the opponent’s immediate checks and mating threats. Handle those before putting pressure on a piece.';
  practice=`From the original position, find a move that prevents ${reply.san}. Explain why the ${NAMES[reply.piece]} cannot deliver the same mate afterward.`;
 }else if(alternative.isCheckmate()){
  pattern='Missed mate in one';title='You had checkmate available immediately';summary=`${first} You could instead play ${best.san}, delivering checkmate on that move.`;
  why.push(`${best.san} checks the king and leaves the opponent with no legal reply. This is an immediate mate, not just a higher engine score.`);
  fix='Check your legal checking moves before calculating quiet alternatives. For each check, test escapes, captures and blocks.';
  practice='Find the mating move from the original position and explain why the king cannot escape.';
 }else if(reply&&balance(actual,played.color)<balance(original,played.color)){
  const lost=balance(original,played.color)-balance(actual,played.color);
  pattern='Material lost in the reply';title='Your move allowed a material-losing reply';summary=`${first} The engine’s reply ${reply.san} leaves your material balance ${lost} point${lost===1?'':'s'} worse in this short line.`;
  why.push(`${side(reply.color)}’s ${moveDescription(reply)}. Compared with the original position, your material balance falls by ${lost} using the usual pawn=1, minor=3, rook=5, queen=9 count.`);
  why.push('This describes the shown reply, not every possible continuation. The engine evaluation also considers compensation and later moves.');
  fix=`Before committing, check the opponent’s captures, especially captures on ${reply.to}. Compare the material after the reply, not just what your own move achieves.`;
  practice=`Find an alternative to ${played.san} and check whether ${reply.san} would still win the same material.`;
 }else if(best.captured||best.san.includes('+')||best.san.includes('#')){
  pattern='Forcing alternatives';title='A forcing alternative deserved attention';summary=`${first} The engine prefers ${best.san}, ${best.captured?`a capture on ${best.to}`:'a check'}, over your move.`;
  why.push(`The alternative ${moveDescription(best)}${best.san.includes('+')?' and gives check':''}. Read the legal engine continuation below to compare the replies.`);
  fix='Start your candidate list with checks and captures, then calculate the opponent’s strongest reply. A forcing move is a candidate, not automatically a good move.';
  practice=`Find the engine’s forcing candidate and calculate the first reply before revealing the line.`;
 }else{
  pattern='Candidate comparison';title='Compare the replies to your candidate moves';summary=`${first} The engine preferred ${best.san}${reply?`, while the leading reply to your move was ${reply.san}`:''}.`;
  why.push('The board alone does not establish a named tactical or strategic cause here. Compare the concrete continuations; this search does not justify a more specific diagnosis.');
  fix='Compare two candidate moves by calculating the opponent’s best response to each. Revisit this example at greater depth if the reason remains unclear.';
  practice=`Compare ${played.san} and another candidate. Write the opponent’s first reply to each, then inspect the engine line.`;
 }
 if(reply){
  const test=new Chess(afterBest),counter=uciMove(test,e.reply);
  if(!counter){
   const df=reply.to.charCodeAt(0)-reply.from.charCodeAt(0),dr=+reply.to[1]- +reply.from[1];
   if(['q','b','r'].includes(reply.piece)&&(df===0||dr===0||Math.abs(df)===Math.abs(dr))){
    const n=Math.max(Math.abs(df),Math.abs(dr)),between=Array.from({length:Math.max(0,n-1)},(_,i)=>String.fromCharCode(reply.from.charCodeAt(0)+Math.sign(df)*(i+1))+(+reply.from[1]+Math.sign(dr)*(i+1)));
    if(between.includes(best.to))better.push(`Your ${NAMES[best.piece]} on ${best.to} blocks the ${NAMES[reply.piece]}’s ${df&&dr?'diagonal':'line'} from ${reply.from} to ${reply.to}.`);
   }
   better.push(`After ${best.san}, the exact reply ${reply.san} is no longer legal. This addresses that reply; it does not claim every threat is gone.`);}
  else if(actual.isCheckmate()&&!test.isCheckmate())better.push(`After ${best.san}, the same reply no longer delivers checkmate.`);
  else if(reply.captured&&counter.captured!==reply.captured)better.push(`After ${best.san}, the same move no longer captures your ${NAMES[reply.captured]}.`);
 }
 if(best.san.includes('+')&&!best.san.includes('#'))better.push('This alternative gives check, so the opponent must respond to the check.');
 return{valid:true,pattern,title,summary,why,better,fix,practice,played:played.san,best:best.san,reply:replyText,line,replyLine:lineSAN(afterPlayed,e.reply?[e.reply]:[]),views:{before:{fen:e.fen,caption:`Before your move. ${side(played.color)} to move.`,marks:[]},played:{fen:afterPlayed,caption:`After your ${played.san}. ${side(played.color==='w'?'b':'w')} to move.`,marks:[played.from,played.to]},best:{fen:afterBest,caption:`After the engine’s alternative ${best.san}. This is an alternative, not the game continuation.`,marks:[best.from,best.to]},...(replyFen?{reply:{fen:replyFen,caption:`After ${played.san} ${replyText} ${isActualReply?'in your game.':'in the engine’s line; it may not have been played in the game.'}`,marks:[reply.from,reply.to]}}:{})}};
}
export function coachingGroups(events,totalGames){
 const groups=new Map();for(const event of events){const story=explainEvent(event);if(!story.valid)continue;const key=story.pattern;if(!groups.has(key))groups.set(key,{title:key,examples:[],gameIds:new Set(),impact:0});const g=groups.get(key);g.examples.push({event,story});g.gameIds.add(event.gameId);g.impact+=Math.min(event.loss||0,1000)}
 return [...groups.values()].map(g=>({...g,games:g.gameIds.size,count:g.examples.length,examples:g.examples.sort((a,b)=>(b.event.loss||0)-(a.event.loss||0)),explanation:`${g.gameIds.size===1?'This appeared in one game':'This repeated in '+g.gameIds.size+' games'} out of ${totalGames} reviewed, with ${g.examples.length} example${g.examples.length===1?'':'s'}. ${g.gameIds.size===1?'Treat it as a finding to check in your next games, not an established recurring weakness.':'The examples below show what repeated; they do not establish why you were thinking that way.'}`})).sort((a,b)=>b.games-a.games||b.impact-a.impact||b.count-a.count);
}
