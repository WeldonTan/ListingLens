"use client"

import { useEffect, useState } from "react"
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
  X
} from "lucide-react"

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
}

export default function DashboardPage() {
  const [activeView, setActiveView] = useState<'dashboard' | 'history'>('dashboard')
  const [listings, setListings] = useState<Listing[]>([])
  const [urls, setUrls] = useState("")
  const [loading, setLoading] = useState(false)
  const [polling, setPolling] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date())
  const [sessionStartTime, setSessionStartTime] = useState<Date>(new Date())
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const sessionListings = listings.filter(l => new Date(l.created_at) > sessionStartTime)
  const displayListings = activeView === 'dashboard' ? sessionListings : listings
  const totalListings = displayListings.length
  const avgPrice = displayListings.length > 0 
    ? displayListings.reduce((acc, curr) => acc + (curr.price || 0), 0) / displayListings.length 
    : 0
  const uniqueStates = new Set(displayListings.map(l => l.state).filter(Boolean)).size

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

  useEffect(() => {
    let interval: NodeJS.Timeout
    let timeout: NodeJS.Timeout

    const checkPollingStatus = async () => {
        const response = await api.get("/listings/")
        setListings(response.data)
        setLastUpdated(new Date())
    }

    if (polling) {
      interval = setInterval(checkPollingStatus, 3000)
      timeout = setTimeout(() => {
        setPolling(false)
      }, 600000) 
    }

    return () => {
        if (interval) clearInterval(interval)
        if (timeout) clearTimeout(timeout)
    }
  }, [polling, sessionStartTime])

  const handleScrape = async () => {
    setLoading(true)
    try {
      const urlList = urls.split("\n").filter((u) => u.trim() !== "")
      if (urlList.length === 0) return

      await api.post("/listings/scrape", { urls: urlList })
      setUrls("")
      setPolling(true)
    } catch (error) {
      console.error("Scraping failed", error)
    } finally {
      setLoading(false)
    }
  }

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

  const ListingsTable = ({ data }: { data: Listing[] }) => (
    <div className="overflow-x-auto rounded-lg border border-slate-100 shadow-sm">
      <table className="w-full text-sm text-left whitespace-nowrap bg-white">
        <thead className="text-xs text-slate-500 uppercase bg-slate-50 border-b border-slate-100 font-display tracking-wider">
          <tr>
            <th className="px-6 py-4 font-bold">Title / Project</th>
            <th className="px-6 py-4 font-bold">Price</th>
            <th className="px-6 py-4 font-bold">Location</th>
            <th className="px-6 py-4 font-bold">Specs</th>
            <th className="px-6 py-4 font-bold">Type</th>
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
                      {listing.bedrooms || "?"} Beds • {listing.bathrooms || "?"} Baths
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[10px] uppercase tracking-wider font-bold bg-blue-50 text-blue-600 border border-blue-100">
                    {listing.property_type || "Unknown"}
                  </span>
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
          </div>
        )}
      </header>

      {/* Main Content */}
      <main className="pt-32 pb-24 container mx-auto px-6 animate-fade-in">
        {/* Hero Section */}
        <div className="mb-12 flex flex-col md:flex-row justify-between md:items-end gap-6 border-b border-slate-200 pb-8">
          <div>
            <h1 className="text-4xl md:text-6xl font-display font-bold text-slate-900 mb-2 tracking-tight">
              {activeView === 'dashboard' ? 'Overview' : 'Archives'}
            </h1>
            <p className="text-lg text-slate-600 max-w-2xl leading-relaxed">
              {activeView === 'dashboard' 
                ? 'Real-time property intelligence and extraction engine.' 
                : 'Complete historical record of all processed property data.'}
            </p>
          </div>
          <div className="flex gap-4">
             {activeView === 'dashboard' && (
                 <Button variant="outline" onClick={() => setSessionStartTime(new Date())} className="border-slate-200 hover:bg-slate-100 text-slate-600">
                    <RefreshCw className="h-4 w-4 mr-2" /> Reset Session
                 </Button>
              )}
             <Button 
                onClick={handleDownloadCSV} 
                disabled={displayListings.length === 0} 
                className="bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl px-6 py-2 shadow-lg shadow-blue-600/20 transition-all hover:-translate-y-0.5"
             >
                <Download className="h-4 w-4 mr-2" />
                Export Data
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
                      {polling && (
                        <span className="flex items-center gap-2 animate-pulse">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Analyzing property data...
                        </span>
                      )}
                   </div>
                   <div className="flex gap-4">
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
              </div>
            </div>

            {/* Recent Results */}
            <div>
              <h3 className="text-xl font-bold font-display text-slate-900 mb-6 flex items-center gap-3">
                 Session Results
                 <span className="text-xs font-sans font-normal text-slate-400 bg-slate-100 px-2 py-1 rounded-full">
                    {sessionListings.length} Items
                 </span>
              </h3>
              <ListingsTable data={sessionListings} />
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-2xl border border-slate-100 shadow-lg p-8">
             <div className="flex justify-between items-center mb-8">
                <h2 className="text-2xl font-bold font-display text-slate-900">Full History</h2>
                <Button variant="destructive" onClick={handleClearHistory} className="bg-red-50 text-red-600 hover:bg-red-100 border-none shadow-none">
                   <Trash2 className="h-4 w-4 mr-2" /> Clear All
                </Button>
             </div>
             <ListingsTable data={listings} />
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
              &copy; {new Date().getFullYear()} Aelion Systems. Internal Use Only.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
