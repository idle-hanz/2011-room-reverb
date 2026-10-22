import { WASI } from 'node:wasi'; import fs from 'node:fs';
const wasi = new WASI({ version: 'preview1', args: [], env: {} });
const m = await WebAssembly.compile(fs.readFileSync(new URL('./src_bench.wasm', import.meta.url)));
const inst = await WebAssembly.instantiate(m, wasi.getImportObject());
wasi.start(inst);
