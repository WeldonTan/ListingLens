"use client"

import { useEffect, useState, useRef } from "react"
import readXlsxFile from 'read-excel-file'
import * as XLSX from 'xlsx'
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { api } from "@/lib/api"
import { 
  LayoutDashboard, 
  Database, 
  Download, 
  RefreshCw, 
  Search, 
  Trash2, 
  ExternalLink,
  Building2,
  MapPin,
  DollarSign,
  Home,
  Loader2,
  Menu,
  X,
  FileUp,
  Wand2,
  Sparkles,
  FileText
} from "lucide-react"

import { cn } from "@/lib/utils"

interface Listing {
  id: number
  url: string
  listing_title: string
  project_name: string
  price: number
  state: string
  area: string
  sq_ft: string
  bedrooms: string
  bathrooms: string
  property_type: string
  carpark: string
  floor_range: string
  phone_number: string
  description: string
  created_at: string
  tenure: string
  furnishing: string
  completion_year: number
}

interface GeneratedContent {
  id: number
  generated_text: string
}

interface ScrapeTask {
  url: string
  taskId: string
  status: string
  result?: any
}

export default function DashboardPage() {
  const [activeView, setActiveView] = useState<'dashboard' | 'history' | 'generate'>('dashboard')
  const [listings, setListings] = useState<Listing[]>([])
  const [urls, setUrls] = useState("")
  const [loading, setLoading] = useState(false)
  const [tasks, setTasks] = useState<ScrapeTask[]>([])
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date())
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [generationInstruction, setGenerationInstruction] = useState("Write a brief, engaging property description for a social media post.")
  const [generatedContent, setGeneratedContent] = useState<GeneratedContent[]>([])
  const [isGenerating, setIsGenerating] = useState(false)

  const fileInputRef = useRef<HTMLInputElement>(null);

  const displayListings = listings
  const totalListings = displayListings.length
  const avgPrice = displayListings.length > 0 
    ? displayListings.reduce((acc, curr) => acc + (curr.price || 0), 0) / displayListings.length 
    : 0
  const uniqueStates = new Set(displayListings.map(l => l.state).filter(Boolean)).size

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      const rows = await readXlsxFile(file);
      // Assuming URLs are in the first column
      const fileUrls = rows.map(row => row[0]).filter(url => typeof url === 'string' && url.startsWith('http')).join('\n');
      setUrls(prev => prev ? `${prev}\n${fileUrls}` : fileUrls);
    } catch (error) {
      console.error("Failed to read Excel file", error);
      alert("Failed to read Excel file. Please ensure it's a valid XLSX file with URLs in the first column.");
    }
    
    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleGenerate = async () => {
    if (listings.length === 0 || !generationInstruction.trim()) return;

    setIsGenerating(true);
    const initialContent = listings.map(l => ({ id: l.id, generated_text: "Generating...", status: "generating" }));
    setGeneratedContent(initialContent as any);

    const generationPromises = listings.map(listing =>
      api.post("/listings/generate-copy", {
        listing_ids: [listing.id],
        instruction: generationInstruction,
      }).then(response => {
        setGeneratedContent(prev =>
          prev.map(c => c.id === listing.id ? { ...response.data[0], status: "completed" } : c)
        );
      }).catch(error => {
        console.error(`Failed to generate content for listing ${listing.id}`, error);
        setGeneratedContent(prev =>
          prev.map(c => c.id === listing.id ? { ...c, generated_text: "Generation failed.", status: "failed" } : c)
        );
      })
    );

    await Promise.all(generationPromises);
    setIsGenerating(false);
  };

  const fetchListings = async (silent = false) => {
    try {
      const response = await api.get("/listings/")
      setListings(response.data)
      setLastUpdated(new Date())
    } catch (error) {
      console.error("Failed to fetch listings", error)
    }
  }

  useEffect(() => {
    fetchListings()
  }, [])

  const handleScrape = async () => {
    const urlList = urls.split("\n").filter((u) => u.trim() !== "")
    if (urlList.length === 0) return

    setLoading(true)
    
    // Optimistically set tasks
    const optimisticTasks = urlList.map((url, index) => ({
      url,
      taskId: `temp-${index}-${Date.now()}`,
      status: "initiating"
    }))
    setTasks(prev => [...optimisticTasks, ...prev])

    try {
      const response = await api.post("/listings/scrape", { urls: urlList })
      
      const newTasks = response.data.task_ids.map((id: string, index: number) => ({
        url: urlList[index],
        taskId: id,
        status: "queued"
      }))
      
      setTasks(prev => {
        const kept = prev.filter(p => !p.taskId.startsWith('temp-'))
        return [...newTasks, ...kept]
      })
      
      setUrls("")
    } catch (error) {
      console.error("Scraping failed", error)
      setTasks(prev => prev.map(t => t.taskId.startsWith('temp-') ? { ...t, status: "failed" } : t))
    } finally {
      setLoading(false)
    }
  }

  const handlePurge = async () => {
    if (!confirm("This will stop all running and queued extraction tasks. Are you sure?")) return
    try {
      await api.post("/listings/scrape/purge")
      setTasks([]) 
    } catch (error) {
      console.error("Failed to purge queue", error)
    }
  }

  useEffect(() => {
    const activeTasks = tasks.filter(t => 
      !t.taskId.startsWith('temp-') && 
      !['complete', 'failed', 'not_found'].includes(t.status)
    )
    
    if (activeTasks.length === 0) return

    const pollStatus = async () => {
      try {
        const taskIds = activeTasks.map(t => t.taskId)
        const response = await api.post("/listings/scrape/status", taskIds)
        const statusData = response.data
        
        let shouldRefreshListings = false

        setTasks(prev => prev.map(t => {
          if (t.taskId.startsWith('temp-')) return t 
          
          const data = statusData[t.taskId]
          if (!data) return t
          
          // Check for error in result even if status is complete
          let newStatus = data.status
          if (newStatus === 'complete' && data.result?.error) {
             newStatus = 'failed'
          }
          
          if (t.status !== 'complete' && newStatus === 'complete') {
             shouldRefreshListings = true
          }

          return {
            ...t,
            status: newStatus,
            result: data.result
          }
        }))

        if (shouldRefreshListings) {
          fetchListings(true)
        }

      } catch (error) {
        console.error("Failed to check status", error)
      }
    }

    const interval = setInterval(pollStatus, 2000)
    return () => clearInterval(interval)
  }, [tasks])

  // Cancel tasks on page unload
  useEffect(() => {
    const handleUnload = () => {
      const activeTasks = tasks.filter(t => 
        !t.taskId.startsWith('temp-') && 
        !['complete', 'failed', 'not_found'].includes(t.status)
      )
      
      if (activeTasks.length > 0) {
        const taskIds = activeTasks.map(t => t.taskId)
        const blob = new Blob([JSON.stringify(taskIds)], {type: 'application/json'});
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"
        navigator.sendBeacon(`${apiUrl}/listings/scrape/cancel`, blob);
      }
    }
    window.addEventListener('beforeunload', handleUnload)
    return () => window.removeEventListener('beforeunload', handleUnload)
  }, [tasks])

  const handleDelete = async (id: number) => {
    if (!confirm("Are you sure you want to delete this listing?")) return
    try {
      await api.delete(`/listings/${id}`)
      fetchListings(true)
    } catch (error) {
      console.error("Failed to delete listing", error)
    }
  }

  const handleClearHistory = async () => {
    if (!confirm("Are you sure you want to delete ALL history? This cannot be undone.")) return
    try {
      await api.delete("/listings/")
      fetchListings(true)
    } catch (error) {
      console.error("Failed to clear history", error)
    }
  }

  const handleDownloadCSV = () => {
    if (listings.length === 0) return
    const headers = [
      "ID", "Title", "Project Name", "Price", "State", "Area", 
      "Type", "Sq Ft", "Beds", "Baths", "Carpark", "Floor Range", 
      "Phone", "Description", "URL"
    ]
    const rows = listings.map(l => [
      l.id, `"${(l.listing_title || "").replace(/"/g, '""')}"`, `"${(l.project_name || "").replace(/"/g, '""')}"`,
      l.price, l.state, l.area, l.property_type, l.sq_ft, l.bedrooms, l.bathrooms, l.carpark, l.floor_range,
      `"${(l.phone_number || "").replace(/"/g, '""')}"`, `"${(l.description || "").replace(/"/g, '""')}"`, l.url
    ])
    const csvContent = [headers.join(","), ...rows.map(row => row.join(","))].join("\n")
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" })
    const link = document.createElement("a")
    const url = URL.createObjectURL(blob)
    link.setAttribute("href", url)
    link.setAttribute("download", `listings_export_${new Date().toISOString().slice(0,10)}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const handleDownloadXLSX = () => {
    if (listings.length === 0) return;
    const headers = [
      "ID", "Title", "Project Name", "Price", "State", "Area", 
      "Type", "Sq Ft", "Beds", "Baths", "Carpark", "Floor Range", 
      "Phone", "Description", "URL"
    ];
    const rows = listings.map(l => ({
      ID: l.id,
      Title: l.listing_title,
      "Project Name": l.project_name,
      Price: l.price,
      State: l.state,
      Area: l.area,
      Type: l.property_type,
      "Sq Ft": l.sq_ft,
      Beds: l.bedrooms,
      Baths: l.bathrooms,
      Carpark: l.carpark,
      "Floor Range": l.floor_range,
      Phone: l.phone_number,
      Description: l.description,
      URL: l.url
    }));

    const worksheet = XLSX.utils.json_to_sheet(rows, { header: headers });
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "Listings");
    XLSX.writeFile(workbook, `listings_export_${new Date().toISOString().slice(0,10)}.xlsx`);
  };

  const handleDownloadContentXLSX = () => {
    if (generatedContent.length === 0) return;

    const rows = listings.map(listing => {
      const content = generatedContent.find(c => c.id === listing.id);
      return {
        ID: listing.id,
        Title: listing.listing_title,
        "Project Name": listing.project_name,
        Price: listing.price,
        State: listing.state,
        Area: listing.area,
        Type: listing.property_type,
        "Sq Ft": listing.sq_ft,
        Beds: listing.bedrooms,
        Baths: listing.bathrooms,
        Carpark: listing.carpark,
        "Floor Range": listing.floor_range,
        Phone: listing.phone_number,
        Description: listing.description,
        URL: listing.url,
        "Generated Content": content ? content.generated_text : "N/A",
      };
    });

    const worksheet = XLSX.utils.json_to_sheet(rows);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "Generated Content");
    XLSX.writeFile(workbook, `content_export_${new Date().toISOString().slice(0,10)}.xlsx`);
  };

  const ListingsTable = ({ data }: { data: Listing[] }) => (
    <div className="overflow-x-auto rounded-lg border border-slate-100 shadow-sm">
      <table className="w-full text-sm text-left whitespace-nowrap bg-white">
        <thead className="text-xs text-slate-500 uppercase bg-slate-50 border-b border-slate-100 font-display tracking-wider">
          <tr>
            <th className="px-6 py-4 font-bold">Title / Project</th>
            <th className="px-6 py-4 font-bold">Price</th>
            <th className="px-6 py-4 font-bold">Location</th>
            <th className="px-6 py-4 font-bold">Specs</th>
            <th className="px-6 py-4 font-bold">Details</th>
            <th className="px-6 py-4 font-bold">Contact</th>
            <th className="px-6 py-4 font-bold text-right">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 font-sans">
          {data.length > 0 ? (
            data.map((listing) => (
              <tr key={listing.id} className="bg-white hover:bg-slate-50/80 transition-colors">
                <td className="px-6 py-4">
                  <div className="font-semibold text-slate-900 truncate max-w-[200px]" title={listing.listing_title}>
                    {listing.listing_title || "Untitled Property"}
                  </div>
                  <div className="text-xs text-blue-600 truncate max-w-[200px] font-medium">{listing.project_name}</div>
                </td>
                <td className="px-6 py-4 font-bold text-slate-900 font-display">
                  {listing.price ? `RM ${listing.price.toLocaleString()}` : "-"}
                </td>
                <td className="px-6 py-4">
                  <div className="text-slate-700">{listing.area}</div>
                  <div className="text-xs text-slate-400 uppercase tracking-wide">{listing.state}</div>
                </td>
                <td className="px-6 py-4 text-slate-600">
                  <div className="flex flex-col gap-1 text-xs font-medium">
                    <span>{listing.sq_ft ? `${listing.sq_ft} sqft` : "-"}</span>
                    <span className="text-slate-400">
                      {listing.bedrooms || "?"} Beds • {listing.bathrooms || "?"} Baths • {listing.carpark || "?"} Carparks
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4 text-slate-600">
                   <div className="flex flex-col gap-1 text-xs font-medium">
                      <span>{listing.property_type || "-"}</span>
                      <span className="text-slate-400">
                        {listing.tenure || "?"} • {listing.furnishing || "?"}
                      </span>
                   </div>
                </td>
                <td className="px-6 py-4 text-sm text-slate-600 font-mono">
                   {listing.phone_number || "-"}
                </td>
                <td className="px-6 py-4 text-right">
                  <div className="flex justify-end gap-2">
                    <a 
                      href={listing.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="inline-flex items-center justify-center p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all"
                    >
                      <ExternalLink className="h-4 w-4" />
                    </a>
                    <button
                      onClick={() => handleDelete(listing.id)}
                      className="inline-flex items-center justify-center p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={7} className="px-6 py-12 text-center text-slate-400">
                <div className="flex flex-col items-center gap-4">
                  <div className="p-4 bg-slate-50 rounded-full">
                    <Database className="h-8 w-8 text-slate-300" />
                  </div>
                  <p className="font-medium">No data available yet.</p>
                </div>
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )

  return (
    <div className="min-h-screen bg-slate-50 font-sans">
      {/* Header */}
      <header className="fixed top-0 w-full h-24 z-50 bg-white/90 backdrop-blur-md border-b border-slate-200 transition-all">
        <div className="container mx-auto px-6 h-full flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Building2 className="h-8 w-8 text-blue-600" />
            <span className="font-display font-bold text-2xl tracking-wide text-slate-900">ListingLens</span>
          </div>
          
          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center gap-8">
            <button 
              onClick={() => setActiveView('dashboard')}
              className={`text-sm uppercase tracking-widest font-bold font-display transition-colors hover:text-blue-600 ${activeView === 'dashboard' ? 'text-blue-600' : 'text-slate-600'}`}
            >
              Dashboard
            </button>
            <button 
              onClick={() => setActiveView('history')}
              className={`text-sm uppercase tracking-widest font-bold font-display transition-colors hover:text-blue-600 ${activeView === 'history' ? 'text-blue-600' : 'text-slate-600'}`}
            >
              History
            </button>
            <button
              onClick={() => setActiveView('generate')}
              className={`text-sm uppercase tracking-widest font-bold font-display transition-colors hover:text-blue-600 ${activeView === 'generate' ? 'text-blue-600' : 'text-slate-600'}`}
            >
              Content Gen
            </button>
          </nav>

          {/* Mobile Menu Toggle */}
          <button className="md:hidden" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
            {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
        
        {/* Mobile Nav */}
        {mobileMenuOpen && (
          <div className="absolute top-24 left-0 w-full bg-white border-b border-slate-200 shadow-xl p-6 flex flex-col gap-4 md:hidden animate-slide-up">
            <button 
              onClick={() => { setActiveView('dashboard'); setMobileMenuOpen(false); }}
              className={`text-left text-sm uppercase tracking-widest font-bold font-display p-2 ${activeView === 'dashboard' ? 'text-blue-600' : 'text-slate-600'}`}
            >
              Dashboard
            </button>
            <button 
              onClick={() => { setActiveView('history'); setMobileMenuOpen(false); }}
              className={`text-left text-sm uppercase tracking-widest font-bold font-display p-2 ${activeView === 'history' ? 'text-blue-600' : 'text-slate-600'}`}
            >
              History
            </button>
            <button 
              onClick={() => { setActiveView('generate'); setMobileMenuOpen(false); }}
              className={`text-left text-sm uppercase tracking-widest font-bold font-display p-2 ${activeView === 'generate' ? 'text-blue-600' : 'text-slate-600'}`}
            >
              Content Gen
            </button>
          </div>
        )}
      </header>

      {/* Main Content */}
      <main className="pt-32 pb-24 container mx-auto px-6 animate-fade-in">
        {/* Hero Section */}
        <div className="mb-12 flex flex-col md:flex-row justify-between md:items-end gap-6 border-b border-slate-200 pb-8">
          <div>
            <h1 className="text-4xl md:text-6xl font-display font-bold text-slate-900 mb-2 tracking-tight">
              {activeView === 'dashboard' ? 'Overview' : activeView === 'history' ? 'Archives' : 'Content Generator'}
            </h1>
            <p className="text-lg text-slate-600 max-w-2xl leading-relaxed">
              {activeView === 'dashboard' 
                ? 'Real-time property intelligence and extraction engine.' 
                : activeView === 'history'
                ? 'Complete historical record of all processed property data.'
                : 'Generate engaging marketing copy for your listings.'}
            </p>
          </div>
          <div className="flex gap-4">
             <Button 
                onClick={handleDownloadXLSX} 
                disabled={displayListings.length === 0} 
                className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-xl px-6 py-2 shadow-lg shadow-emerald-600/20 transition-all hover:-translate-y-0.5"
             >
                <FileText className="h-4 w-4 mr-2" />
                Export Excel
             </Button>
             <Button 
                onClick={handleDownloadCSV} 
                disabled={displayListings.length === 0} 
                className="bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl px-6 py-2 shadow-lg shadow-blue-600/20 transition-all hover:-translate-y-0.5"
             >
                <Download className="h-4 w-4 mr-2" />
                Export CSV
             </Button>
          </div>
        </div>

        {activeView === 'dashboard' ? (
          <div className="space-y-12">
            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {[
                { label: "Total Properties", value: totalListings, icon: Home, color: "text-blue-600", bg: "bg-blue-50" },
                { label: "Average Price", value: avgPrice ? `RM ${avgPrice.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : "N/A", icon: DollarSign, color: "text-emerald-600", bg: "bg-emerald-50" },
                { label: "States Covered", value: uniqueStates, icon: MapPin, color: "text-purple-600", bg: "bg-purple-50" }
              ].map((stat, i) => (
                <div key={i} className="bg-white p-8 rounded-2xl border border-slate-100 shadow-lg hover:-translate-y-1 transition-transform duration-300">
                  <div className={`w-12 h-12 ${stat.bg} rounded-xl flex items-center justify-center mb-4`}>
                    <stat.icon className={`h-6 w-6 ${stat.color}`} />
                  </div>
                  <p className="text-sm font-bold uppercase tracking-wider text-slate-400 font-display">{stat.label}</p>
                  <h3 className="text-3xl font-bold text-slate-900 mt-1 font-display">{stat.value}</h3>
                </div>
              ))}
            </div>

            {/* Input Section */}
            <div className="bg-white rounded-2xl border border-slate-100 shadow-lg p-8 md:p-10 relative overflow-hidden">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-400 to-cyan-300"></div>
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-blue-50 rounded-lg">
                  <Search className="h-6 w-6 text-blue-600" />
                </div>
                <div>
                  <h2 className="text-2xl font-bold font-display text-slate-900">New Extraction</h2>
                  <p className="text-slate-500">Paste listing URLs to begin analysis</p>
                </div>
              </div>
              
              <div className="space-y-6">
                <textarea
                  className="w-full min-h-[150px] rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all resize-y"
                  value={urls}
                  onChange={(e) => setUrls(e.target.value)}
                  placeholder="https://www.mudah.my/..."
                  disabled={loading}
                />
                
                <div className="flex justify-between items-center">
                   <div className="text-sm font-medium text-blue-600">
                        <input
                          type="file"
                          ref={fileInputRef}
                          onChange={handleFileChange}
                          className="hidden"
                          accept=".xlsx"
                        />
                        <Button variant="outline" onClick={() => fileInputRef.current?.click()} className="border-slate-200 hover:bg-slate-100 text-slate-600">
                          <FileUp className="h-4 w-4 mr-2" />
                          Import Excel
                        </Button>
                   </div>
                   <div className="flex gap-4">
                      <Button variant="ghost" onClick={handlePurge} className="text-red-500 hover:text-red-700 hover:bg-red-50">Stop All</Button>
                      <Button variant="ghost" onClick={() => setUrls("")} className="text-slate-500 hover:text-slate-900">Clear</Button>
                      <Button 
                        onClick={handleScrape} 
                        disabled={loading || !urls.trim()}
                        className="bg-slate-900 hover:bg-slate-800 text-white px-8 py-6 rounded-xl font-semibold text-lg shadow-xl shadow-slate-900/10 transition-all hover:scale-105"
                      >
                        {loading ? <Loader2 className="animate-spin" /> : "Start Extraction"}
                      </Button>
                   </div>
                </div>

                {tasks.length > 0 && (
                  <div className="mt-8 space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
                    <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 font-display flex items-center gap-2">
                       <RefreshCw className={cn("h-4 w-4", loading ? "animate-spin" : "")} />
                       Extraction Session
                    </h3>
                    <div className="space-y-3">
                      {tasks.map((task) => (
                        <div key={task.taskId} className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-col gap-3 transition-all hover:border-blue-300 hover:shadow-md animate-in fade-in zoom-in-95 duration-300">
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-medium text-slate-700 truncate flex-1 mr-4 flex items-center gap-2">
                               <ExternalLink className="h-3 w-3 text-slate-400" />
                               {task.url}
                            </span>
                            <div className="flex items-center gap-2 shrink-0">
                                {['in_progress', 'queued', 'initiating'].includes(task.status) && (
                                  <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                                )}
                                <span className={cn(
                                  "px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider shadow-sm",
                                  task.status === 'complete' ? 'bg-emerald-100 text-emerald-700 border border-emerald-200' : 
                                  task.status === 'failed' ? 'bg-red-100 text-red-700 border border-red-200' : 
                                  ['in_progress', 'queued', 'initiating'].includes(task.status) ? 'bg-blue-50 text-blue-700 border border-blue-100' :
                                  'bg-slate-100 text-slate-600 border border-slate-200'
                                )}>
                                  {task.status === 'in_progress' ? 'Analyzing...' : 
                                   task.status === 'initiating' ? 'Initiating...' :
                                   task.status === 'queued' ? 'Queued' :
                                   task.status === 'complete' ? 'Completed' : 
                                   task.status.replace('_', ' ')}
                                </span>
                            </div>
                          </div>
                          
                          {task.result && task.status === 'complete' && (
                            <div className="bg-slate-50/50 rounded-lg p-4 text-sm border border-slate-100 mt-1 animate-in fade-in slide-in-from-top-2">
                               <p className="font-bold text-slate-900 font-display text-base">{task.result.listing_title || task.result.project_name || "Extracted Successfully"}</p>
                               <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-3 text-xs text-slate-600">
                                  {task.result.price && (
                                      <div className="flex flex-col">
                                          <span className="text-slate-400 uppercase text-[10px] font-bold">Price</span>
                                          <span className="font-mono text-emerald-600 font-bold text-sm">RM {task.result.price.toLocaleString()}</span>
                                      </div>
                                  )}
                                  {task.result.sq_ft && (
                                      <div className="flex flex-col">
                                          <span className="text-slate-400 uppercase text-[10px] font-bold">Size</span>
                                          <span>{task.result.sq_ft.toLocaleString()} sqft</span>
                                      </div>
                                  )}
                                  {task.result.area && (
                                      <div className="flex flex-col">
                                          <span className="text-slate-400 uppercase text-[10px] font-bold">Location</span>
                                          <span>{task.result.area}</span>
                                      </div>
                                  )}
                                  {task.result.phone_number && (
                                      <div className="flex flex-col">
                                          <span className="text-slate-400 uppercase text-[10px] font-bold">Contact</span>
                                          <span className="text-blue-600 font-mono">{task.result.phone_number}</span>
                                      </div>
                                  )}
                               </div>
                            </div>
                          )}
                          {task.status === 'failed' && (
                             <div className="text-xs text-red-600 bg-red-50 p-3 rounded-lg border border-red-100 animate-in fade-in">
                                Extraction failed. Please verify the URL is correct and accessible.
                             </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

              </div>
            </div>
          </div>
        ) : activeView === 'history' ? (
          <div className="bg-white rounded-2xl border border-slate-100 shadow-lg p-8">
             <div className="flex justify-between items-center mb-8">
                <h2 className="text-2xl font-bold font-display text-slate-900">Full History</h2>
                <Button variant="destructive" onClick={handleClearHistory} className="bg-red-50 text-red-600 hover:bg-red-100 border-none shadow-none">
                   <Trash2 className="h-4 w-4 mr-2" /> Clear All
                </Button>
             </div>
             <ListingsTable data={listings} />
          </div>
        ) : (
          <div className="space-y-12">
            {/* Generator Input */}
            <div className="bg-white rounded-2xl border border-slate-100 shadow-lg p-8 md:p-10 relative overflow-hidden">
               <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-purple-400 to-pink-400"></div>
                <div className="flex items-center gap-3 mb-6">
                  <div className="p-2 bg-purple-50 rounded-lg">
                    <Wand2 className="h-6 w-6 text-purple-600" />
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold font-display text-slate-900">AI Content Generator</h2>
                    <p className="text-slate-500">Generate copy for the {listings.length} listings in the current session.</p>
                  </div>
                </div>

                <div className="space-y-6">
                  <textarea
                    className="w-full min-h-[100px] rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500 transition-all resize-y"
                    value={generationInstruction}
                    onChange={(e) => setGenerationInstruction(e.target.value)}
                    placeholder="e.g., Follow up with the owner for interest to sell or rent..."
                    disabled={isGenerating}
                  />
                  <div className="flex justify-end">
                    <Button 
                      onClick={handleGenerate} 
                      disabled={isGenerating || listings.length === 0}
                      className="bg-purple-600 hover:bg-purple-700 text-white px-8 py-6 rounded-xl font-semibold text-lg shadow-xl shadow-purple-600/10 transition-all hover:scale-105"
                    >
                      {isGenerating ? <Loader2 className="animate-spin" /> : "Generate"}
                    </Button>
                  </div>
                </div>
            </div>

            {/* Generation Results */}
            {(isGenerating || generatedContent.length > 0) && (
              <div className="space-y-8">
                <div className="flex justify-between items-center">
                  <h3 className="text-xl font-bold font-display text-slate-900 flex items-center gap-3">
                    <Sparkles className="h-5 w-5 text-purple-500" />
                    Generated Content
                  </h3>
                  <Button 
                    onClick={handleDownloadContentXLSX} 
                    disabled={isGenerating || generatedContent.filter(c => (c as any).status === 'completed').length === 0}
                    variant="outline"
                    className="border-emerald-200 hover:bg-emerald-100 text-emerald-600"
                  >
                    <FileText className="h-4 w-4 mr-2" />
                    Export Content
                  </Button>
                </div>
                {listings.map(listing => {
                    const content = generatedContent.find(c => c.id === listing.id) as any;
                    if (!content) return null;
                    return (
                        <div key={listing.id} className="bg-white rounded-2xl border border-slate-100 shadow-lg p-8">
                          <div className="flex justify-between items-start">
                            <h4 className="font-bold text-blue-600 font-display text-lg mb-2 flex-1">{listing.listing_title || 'Untitled'}</h4>
                            <div className="flex items-center gap-2">
                                {content.status === 'generating' && (
                                  <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                                )}
                                <span className={cn(
                                  "px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider shadow-sm",
                                  content.status === 'completed' ? 'bg-emerald-100 text-emerald-700 border border-emerald-200' : 
                                  content.status === 'failed' ? 'bg-red-100 text-red-700 border border-red-200' : 
                                  'bg-blue-50 text-blue-700 border border-blue-100'
                                )}>
                                  {content.status}
                                </span>
                            </div>
                          </div>
                          <div className="prose prose-sm max-w-none text-slate-700 whitespace-pre-wrap mt-2">{content.generated_text}</div>
                        </div>
                    )
                })}
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-16 mt-24">
        <div className="container mx-auto px-6">
          <div className="flex flex-col md:flex-row justify-between items-center gap-6">
            <div className="flex items-center gap-2 grayscale opacity-50 hover:grayscale-0 hover:opacity-100 transition-all">
               <Building2 className="h-6 w-6" />
               <span className="font-display font-bold text-lg">ListingLens</span>
            </div>
            <p className="text-slate-400 text-sm">
              &copy; {new Date().getFullYear()} Aelion Systems. All Rights Reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
