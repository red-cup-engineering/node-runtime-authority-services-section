import test from 'node:test';
import assert from 'node:assert/strict';
import { decodeTexPlate } from '../src/index.mjs';
test('reads TeX structure, dependencies and references without a proof assistant', () => {
  const plate = decodeTexPlate(String.raw`\usepackage{amsmath}
\input{chapter}
\begin{equation}[Balance]
\label{eq:balance}
x = y % ignored \ref{not-a-reference}
\end{equation}
See \eqref{eq:balance}.`, { source: 'paper.tex' });
  assert.deepEqual(plate.dependencies.map(({kind, target}) => [kind,target]), [['package','amsmath'],['input','chapter']]);
  assert.deepEqual(plate.environments, [{name:'equation',title:'Balance',line:3}]);
  assert.deepEqual(plate.labels, [{name:'eq:balance',line:4}]);
  assert.deepEqual(plate.references.map(({target}) => target), ['eq:balance']);
});
