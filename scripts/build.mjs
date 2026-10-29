import {build} from 'esbuild';import {mkdir,copyFile,readFile,writeFile} from 'node:fs/promises';
await mkdir('dist/engine',{recursive:true});await build({entryPoints:['src/app.js'],bundle:true,format:'esm',outfile:'dist/app.js'});
for(const n of ['index.html','style.css'])await copyFile('web/'+n,'dist/'+n);
for(const n of ['stockfish-18-lite-single.js','stockfish-18-lite-single.wasm'])await copyFile('node_modules/stockfish/bin/'+n,'dist/engine/'+n);
await copyFile('node_modules/stockfish/Copying.txt','dist/engine/LICENSE.txt');
await writeFile('dist/engine/SOURCE.txt','Stockfish.js 18.0.8 / Stockfish 18, GPL-3.0. Corresponding source and build instructions: https://github.com/nmrugg/stockfish.js/tree/v18.0.8\nPackage: https://www.npmjs.com/package/stockfish/v/18.0.8\n');
