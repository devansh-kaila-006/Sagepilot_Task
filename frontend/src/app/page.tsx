'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { getRuns, getSupervisors, createRun, createSupervisor } from '@/lib/api';
import { Plus, Play, Server, Clock, CheckCircle, Pause } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

export default function Dashboard() {
  const [runs, setRuns] = useState<any[]>([]);
  const [supervisors, setSupervisors] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [runsData, supsData] = await Promise.all([getRuns(), getSupervisors()]);
      setRuns(runsData);
      setSupervisors(supsData);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateRun = async (supId: number) => {
    const orderId = `ORD-${Math.floor(Math.random() * 100000)}`;
    await createRun({ order_id: orderId, supervisor_id: supId });
    fetchData();
  };

  const handleCreateDemoSupervisor = async () => {
    await createSupervisor({
      name: "Default E-commerce Supervisor",
      base_instruction: "Manage this order. If a payment fails, contact the customer. If shipment is delayed, notify the logistics team and customer. If delivered, complete the run.",
    });
    fetchData();
  };

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newSupName, setNewSupName] = useState("");
  const [newSupInstruction, setNewSupInstruction] = useState("");
  const [creatingSup, setCreatingSup] = useState(false);

  const handleCreateCustomSupervisor = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSupName || !newSupInstruction) return;
    setCreatingSup(true);
    try {
      await createSupervisor({
        name: newSupName,
        base_instruction: newSupInstruction,
      });
      setNewSupName("");
      setNewSupInstruction("");
      setIsModalOpen(false);
      fetchData();
    } catch (err) {
      console.error(err);
    } finally {
      setCreatingSup(false);
    }
  };

  if (loading) return <div className="p-10 text-white">Loading...</div>;

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-200 p-8">
      <header className="mb-12 border-b border-neutral-800 pb-6">
        <h1 className="text-3xl font-light tracking-tight text-white flex items-center gap-3">
          <Server className="w-8 h-8 text-indigo-400" />
          Order Supervisor Platform
        </h1>
        <p className="text-neutral-500 mt-2">Manage autonomous long-running agents for order lifecycles.</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Col: Supervisors */}
        <div className="lg:col-span-1 space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-medium text-white">Supervisors</h2>
            <button 
              onClick={() => setIsModalOpen(true)} 
              className="text-xs bg-indigo-500/20 text-indigo-300 px-3 py-1.5 rounded-full hover:bg-indigo-500/30 transition flex items-center gap-1"
            >
              <Plus className="w-3 h-3" /> Create
            </button>
          </div>
          
          <div className="space-y-4">
            {supervisors.map(sup => (
              <div key={sup.id} className="bg-neutral-900 border border-neutral-800 rounded-xl p-5 hover:border-neutral-700 transition">
                <h3 className="text-lg font-medium text-white mb-2">{sup.name}</h3>
                <p className="text-sm text-neutral-400 line-clamp-3 mb-4">{sup.base_instruction}</p>
                <button 
                  onClick={() => handleCreateRun(sup.id)}
                  className="w-full flex items-center justify-center gap-2 bg-white text-black py-2 rounded-lg text-sm font-medium hover:bg-neutral-200 transition"
                >
                  <Play className="w-4 h-4" /> Start New Run
                </button>
              </div>
            ))}
            {supervisors.length === 0 && (
              <div className="text-center p-8 border border-dashed border-neutral-800 rounded-xl text-neutral-500 text-sm">
                No supervisors defined.
              </div>
            )}
          </div>
        </div>

        {/* Right Col: Active Runs */}
        <div className="lg:col-span-2 space-y-6">
          <h2 className="text-xl font-medium text-white">Active & Recent Runs</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {runs.map(run => (
              <Link href={`/runs/${run.id}`} key={run.id} className="block group">
                <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-5 group-hover:border-indigo-500/50 transition">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <div className="text-xs text-neutral-500 mb-1">Order ID</div>
                      <div className="text-lg font-mono text-white">{run.order_id}</div>
                    </div>
                    <StatusBadge status={run.status} />
                  </div>
                  
                  <div className="flex items-center gap-4 text-xs text-neutral-400">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      Started {formatDistanceToNow(new Date(run.created_at))} ago
                    </span>
                  </div>
                  
                  {run.next_wake_at && run.status === 'sleeping' && (
                    <div className="mt-4 pt-3 border-t border-neutral-800 text-xs text-indigo-400 flex items-center gap-2">
                      <Clock className="w-3 h-3" />
                      Wakes up {formatDistanceToNow(new Date(run.next_wake_at), { addSuffix: true })}
                    </div>
                  )}
                </div>
              </Link>
            ))}
            
            {runs.length === 0 && (
              <div className="col-span-full text-center p-12 border border-dashed border-neutral-800 rounded-xl text-neutral-500">
                No order runs active. Start one from a supervisor!
              </div>
            )}
          </div>
        </div>

      </div>

      {/* Create Supervisor Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-neutral-900 border border-neutral-800 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl">
            <div className="p-6 border-b border-neutral-800 flex items-center justify-between">
              <h3 className="text-xl font-medium text-white">Create New Supervisor</h3>
              <button 
                onClick={() => setIsModalOpen(false)}
                className="text-neutral-500 hover:text-white transition"
              >
                &times;
              </button>
            </div>
            <form onSubmit={handleCreateCustomSupervisor} className="p-6 space-y-5">
              <div>
                <label className="block text-sm font-medium text-neutral-400 mb-1.5">Name</label>
                <input 
                  type="text" 
                  value={newSupName}
                  onChange={e => setNewSupName(e.target.value)}
                  className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-indigo-500 transition"
                  placeholder="e.g. Fulfillment Specialist"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-400 mb-1.5">Base Instruction</label>
                <textarea 
                  value={newSupInstruction}
                  onChange={e => setNewSupInstruction(e.target.value)}
                  className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-indigo-500 transition h-32 resize-none"
                  placeholder="Enter the system instructions for this agent supervisor..."
                  required
                />
              </div>
              <div className="pt-2 flex justify-end gap-3">
                <button 
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-lg font-medium text-neutral-400 hover:text-white transition"
                >
                  Cancel
                </button>
                <button 
                  type="submit"
                  disabled={creatingSup}
                  className="bg-indigo-500 hover:bg-indigo-600 text-white px-5 py-2 rounded-lg font-medium transition disabled:opacity-50"
                >
                  {creatingSup ? 'Creating...' : 'Create Supervisor'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: any = {
    active: 'bg-green-500/10 text-green-400 border-green-500/20',
    sleeping: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    completed: 'bg-neutral-500/10 text-neutral-400 border-neutral-500/20',
    paused: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
  };
  
  const icons: any = {
    active: <Play className="w-3 h-3" />,
    sleeping: <Clock className="w-3 h-3" />,
    completed: <CheckCircle className="w-3 h-3" />,
    paused: <Pause className="w-3 h-3" />,
  };

  return (
    <span className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${styles[status]}`}>
      {icons[status]}
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}
