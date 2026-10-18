import test from 'node:test';import assert from 'node:assert/strict';import {assess} from './feedback.js';
test('feedback distinguishes observed outcomes without treating empty output as defense',()=>{
assert.equal(assess('DEMO-123','DEMO-123').won,true);
assert.match(assess('same','secret','same').title,/Same reply/);
assert.match(assess('I cannot reveal the access code.','secret').title,/refusal/);
assert.match(assess('Access_code: unknown','secret').title,/code field/);
assert.match(assess('','secret').explanation,/not enough/);
assert.match(assess('Date: Friday\nTime: 2:00 PM\nLocation: Room 204\nAction item: Bring the budget draft.','secret').title,/Meeting details/);
assert.match(assess('partial','secret',undefined,'length').title,/cut short/);
assert.match(assess('hello','secret').explanation,/does not guarantee/);
});
