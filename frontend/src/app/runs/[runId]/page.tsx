'use client';

import { useEffect, useState, use } from 'react';
import Link from 'next/link';
import { getRun, getRunActivities, injectEvent, injectInstruction, terminateRun, pauseRun, resumeRun } from '@/lib/api';
import { supabase } from '@/lib/supabaseClient';
import { ArrowLeft, Send, Zap, ShieldAlert, Activity, StopCircle, PlayCircle, PauseCircle } from 'lucide-react';
import { format } from 'date-fns';

export default function RunDetail({ params }: { params: Promise<{ runId: string }> }) {
  const resolvedParams = use(params);
  const { runId } = resolvedParams;

  const [run, setRun] = useState<any>(null);
  const [activities, setActivities] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Form states
  const [instructionText, setInstructionText] = useState('');
  const [selectedEvent, setSelectedEvent] = useState('payment_failed');
  const [streamEvents, setStreamEvents] = useState<any[]>([]);

  useEffect(() => {
    fetchData();
    
    // Supabase Realtime Subscription for Activities
    const subscription = supabase
      .channel(`run_activities_${runId}`)
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'activities', filter: `run_id=eq.${runId}` }, payload => {
        setActivities(current => {
          if (current.some(act => act.id === payload.new.id)) return current;
          return [...current, payload.new];
        });
      })
      .on('postgres_changes', { event: 'UPDATE', schema: 'public', table: 'runs', filter: `id=eq.${runId}` }, payload => {
        setRun(payload.new);
      })
      .subscribe();

    let ws: WebSocket | null = null;
    let isMounted = true;
    
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!isMounted) return;
      const token = session?.access_token || '';
      
      const wsProtocol = process.env.NEXT_PUBLIC_API_URL?.startsWith('https') ? 'wss' : 'ws';
      const wsHost = process.env.NEXT_PUBLIC_API_URL?.replace(/^https?:\/\//, '') || 'localhost:8000/api';
      const wsUrl = `${wsProtocol}://${wsHost}/runs/${runId}/stream?token=${token}`;
      
      ws = new WebSocket(wsUrl);
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        setStreamEvents(prev => {
          const newEvents = [...prev];
          const lastEvent = newEvents[newEvents.length - 1];
          
          if (
            lastEvent && 
            data.kind === 'on_chat_model_stream' && 
            lastEvent.kind === 'on_chat_model_stream' &&
            lastEvent.name === data.name
          ) {
            // Combine chunks safely with immutability
            const updatedEvent = {
              ...lastEvent,
              content: (lastEvent.content || '') + (data.content || '')
            };
            newEvents[newEvents.length - 1] = updatedEvent;
            return newEvents;
          }
          
          return [...newEvents.slice(-49), data];
        });
      };
    });

    return () => {
      isMounted = false;
      supabase.removeChannel(subscription);
      if (ws) ws.close();
    };
  }, [runId]);

  const fetchData = async () => {
    try {
      const [runData, actsData] = await Promise.all([getRun(runId), getRunActivities(runId)]);
      setRun(runData);
      setActivities(actsData);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleInjectEvent = async () => {
    await injectEvent(runId, { event: selectedEvent, message: `System emitted ${selectedEvent}` });
    fetchData();
  };

  const handleInjectInstruction = async () => {
    if (!instructionText) return;
    await injectInstruction(runId, instructionText);
    setInstructionText('');
    fetchData();
  };

  if (loading) return <div className="p-10 text-white">Loading run...</div>;
  if (!run) return <div className="p-10 text-white">Run not found</div>;

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-200">
      <header className="bg-neutral-900 border-b border-neutral-800 p-6 flex justify-between items-center sticky top-0 z-10">
        <div className="flex items-center gap-4">
          <Link href="/" className="text-neutral-400 hover:text-white transition">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-xl font-mono text-white">Order: {run.order_id}</h1>
            <div className="text-xs text-neutral-500">Run ID: {run.id}</div>
          </div>
        </div>
        
        <div className="flex gap-2">
          {run.status === 'active' && <button onClick={() => pauseRun(run.id).then(fetchData)} className="p-2 bg-neutral-800 text-yellow-400 rounded-md hover:bg-neutral-700"><PauseCircle className="w-5 h-5" /></button>}
          {run.status === 'paused' && <button onClick={() => resumeRun(run.id).then(fetchData)} className="p-2 bg-neutral-800 text-green-400 rounded-md hover:bg-neutral-700"><PlayCircle className="w-5 h-5" /></button>}
          {run.status !== 'completed' && <button onClick={() => terminateRun(run.id).then(fetchData)} className="p-2 bg-neutral-800 text-red-400 rounded-md hover:bg-neutral-700"><StopCircle className="w-5 h-5" /></button>}
          <div className="px-3 py-1.5 bg-neutral-800 border border-neutral-700 rounded-md text-sm font-medium ml-4 uppercase tracking-wider">
            {run.status}
          </div>
        </div>
      </header>

      <div className="flex flex-col lg:flex-row h-[calc(100vh-89px)]">
        
        {/* Left: Timeline */}
        <div className="lg:w-2/3 p-8 overflow-y-auto border-r border-neutral-800">
          <h2 className="text-xl font-medium mb-6 flex items-center gap-2"><Activity className="w-5 h-5 text-indigo-400" /> Activity Log</h2>
          
          <div className="space-y-6 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-neutral-800 before:to-transparent">
            {activities.map((act) => (
              <div key={act.id} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                <div className="flex items-center justify-center w-10 h-10 rounded-full border border-neutral-800 bg-neutral-900 text-neutral-500 shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 shadow">
                  <ActivityIcon type={act.type} />
                </div>
                
                <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] bg-neutral-900 border border-neutral-800 rounded-xl p-4 shadow">
                  <div className="flex justify-between items-start mb-1">
                    <span className="font-semibold text-white text-sm uppercase tracking-wider">{act.type}</span>
                    <span className="text-xs text-neutral-500">{format(new Date(act.created_at), 'HH:mm:ss')}</span>
                  </div>
                  <pre className="text-xs text-neutral-400 whitespace-pre-wrap font-mono mt-2 bg-neutral-950 p-2 rounded border border-neutral-800">
                    {JSON.stringify(act.payload, null, 2)}
                  </pre>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Controls & Memory */}
        <div className="lg:w-1/3 p-8 overflow-y-auto bg-neutral-900">
          
          <div className="mb-8">
            <h3 className="text-sm font-medium text-neutral-400 uppercase tracking-wider mb-4 flex items-center gap-2">
              <Zap className="w-4 h-4 text-yellow-400" /> Inject Event
            </h3>
            <div className="flex gap-2">
              <select 
                value={selectedEvent} 
                onChange={(e) => setSelectedEvent(e.target.value)}
                className="bg-neutral-950 border border-neutral-800 text-sm rounded-lg flex-1 p-2 focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="payment_confirmed">Payment Confirmed</option>
                <option value="payment_failed">Payment Failed</option>
                <option value="shipment_created">Shipment Created</option>
                <option value="shipment_delayed">Shipment Delayed</option>
                <option value="delivered">Delivered</option>
                <option value="refund_requested">Refund Requested</option>
                <option value="customer_message_received">Customer Message</option>
              </select>
              <button 
                onClick={handleInjectEvent}
                disabled={run.status === 'completed'}
                className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50"
              >
                Send
              </button>
            </div>
          </div>

          <div className="mb-8">
            <h3 className="text-sm font-medium text-neutral-400 uppercase tracking-wider mb-4 flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-indigo-400" /> Add Instruction
            </h3>
            <textarea
              value={instructionText}
              onChange={(e) => setInstructionText(e.target.value)}
              placeholder="e.g. For this order, prioritize speed over cost."
              className="w-full bg-neutral-950 border border-neutral-800 rounded-lg p-3 text-sm focus:ring-indigo-500 focus:border-indigo-500 mb-2 h-24"
            />
            <button 
              onClick={handleInjectInstruction}
              disabled={run.status === 'completed'}
              className="w-full flex items-center justify-center gap-2 bg-white text-black hover:bg-neutral-200 px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50"
            >
              <Send className="w-4 h-4" /> Send Instruction
            </button>
          </div>

          <div>
            <h3 className="text-sm font-medium text-neutral-400 uppercase tracking-wider mb-4">
              Agent State
            </h3>
            <div className="bg-neutral-950 border border-neutral-800 rounded-lg p-4 font-mono text-xs text-neutral-400 overflow-x-auto mb-8">
              <div><strong>Status:</strong> {run.status}</div>
              {run.next_wake_at && <div><strong>Wakes at:</strong> {format(new Date(run.next_wake_at), 'PPp')}</div>}
            </div>
          </div>

          <div>
            <h3 className="text-sm font-medium text-neutral-400 uppercase tracking-wider mb-4 flex items-center gap-2">
              <Activity className="w-4 h-4 text-green-400" /> Live Agent Feed
            </h3>
            <div className="bg-neutral-950 border border-neutral-800 rounded-lg p-4 font-mono text-xs text-neutral-400 h-64 overflow-y-auto">
              {streamEvents.length === 0 ? (
                <div className="text-neutral-600 italic">Waiting for agent activity...</div>
              ) : (
                streamEvents.map((ev, i) => (
                  <div key={i} className="mb-3 pb-3 border-b border-neutral-900 last:border-0">
                    <span className="text-indigo-400 font-semibold uppercase tracking-wider text-[10px]">
                      {ev.name === 'ChatGoogleGenerativeAI' ? 'Agent Thinking' : ev.name.replace(/_/g, ' ')}
                    </span>
                    {ev.content && <span className="text-white ml-2 block mt-1.5 leading-relaxed">{ev.content}</span>}
                    {ev.input && <pre className="text-neutral-500 mt-2 bg-neutral-900/50 p-2 rounded">{JSON.stringify(ev.input)}</pre>}
                    {ev.output && <pre className="text-green-500/90 mt-2 bg-green-500/5 p-2 rounded">{ev.output}</pre>}
                  </div>
                ))
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

function ActivityIcon({ type }: { type: string }) {
  if (type === 'event') return <Zap className="w-4 h-4 text-yellow-400" />;
  if (type === 'instruction') return <ShieldAlert className="w-4 h-4 text-indigo-400" />;
  if (type === 'action') return <Activity className="w-4 h-4 text-green-400" />;
  if (type === 'sleep') return <StopCircle className="w-4 h-4 text-blue-400" />;
  if (type === 'wake') return <PlayCircle className="w-4 h-4 text-blue-400" />;
  return <div className="w-2 h-2 rounded-full bg-neutral-500" />;
}
