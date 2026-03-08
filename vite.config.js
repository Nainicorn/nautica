import { defineConfig } from 'vite';
import fs from 'fs';
import path from 'path';

const hbsLoader = {
    name: 'hbs-loader',
    resolveId(id) {
        if (id.endsWith('.hbs')) {
            return { id, moduleSideEffects: false };
        }
    },
    load(id) {
        if (id.endsWith('.hbs')) {
            const content = fs.readFileSync(id, 'utf-8');
            return `import Handlebars from 'handlebars';
const template = Handlebars.compile(${JSON.stringify(content)});
export default function(context) {
  return template(context || {});
}`;
        }
    }
};

export default defineConfig({
    plugins: [hbsLoader],
    root: './',
    publicDir: 'public',
    server: {
        port: 5001,
        host: 'localhost',
        proxy: {
            '/api': {
                target: 'http://localhost:5002',
                changeOrigin: true,
                timeout: 0,
                proxyTimeout: 0,
            }
        }
    },
    build: {
        outDir: 'dist',
        emptyOutDir: true,
    },
    resolve: {
        alias: {
            '@ui': path.resolve(import.meta.dirname, 'ui'),
            '@components': path.resolve(import.meta.dirname, 'ui/components'),
        }
    }
});
