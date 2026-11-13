import {test} from 'node:test';
import assert from 'node:assert/strict';
import {criteria,screen,literatureMetrics} from './convergence.mjs';

test('temporal screen separates startup, steady and changing profiles',()=>{
  const records=Array.from({length:241},(_,i)=>({time_s:i*.005,
    h10:[{r:0,T:300,CO:0},{r:.01,T:2000,CO:.04}],
    h40:[{r:0,T:1450,CO:.03},{r:.01,T:2000,CO:.04}]}));
  assert.equal(screen(records.filter(p=>p.time_s<criteria.minimum_time_s)).provisionally_steady,false);
  assert.equal(screen(records).provisionally_steady,true);
  const moving=records.map(p=>({...p,h40:p.h40.map(r=>({...r,T:r.T+1000*p.time_s}))}));
  assert.equal(screen(moving).provisionally_steady,false);
});

test('literature errors use covered raw coordinates, not display interpolation',()=>{
  const rows=[{r:0,T:300,CO:0},{r:.01,T:1300,CO:.04}];
  const metrics=literatureMetrics({h10:rows,h40:rows},{curves:[
    {height_m:.01,quantity:'T_K',points:[{r_m:.005,value:800},{r_m:.02,value:300}]}]});
  assert.equal(metrics[0].RMSE,0);
  assert.equal(metrics[0].covered,1);assert.equal(metrics[0].total,2);
});
