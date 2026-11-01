import {useEffect,useRef} from 'react';
import Plotly from 'plotly.js-basic-dist-min';
import type {Data,Layout} from 'plotly.js';
export default function Chart({data,layout,label}:{data:Data[];layout:Partial<Layout>;label:string}){
 const ref=useRef<HTMLDivElement>(null);
 useEffect(()=>{
  const el=ref.current!;
  const height=layout.height??330;
  el.style.height=`${height}px`;
  void Plotly.react(el,data,{autosize:true,height,paper_bgcolor:'transparent',plot_bgcolor:'transparent',font:{family:'Inter, system-ui, sans-serif',color:'#6b778b',size:11},margin:{l:58,r:22,t:22,b:56},showlegend:false,...layout},{responsive:true,displaylogo:false,modeBarButtonsToRemove:['lasso2d','select2d']});
  const obs=new ResizeObserver(()=>{void Plotly.Plots.resize(el)});
  obs.observe(el);return()=>{obs.disconnect();Plotly.purge(el)};
 },[data,layout]);
 return <div ref={ref} className="plot" role="img" aria-label={label}/>;
}
