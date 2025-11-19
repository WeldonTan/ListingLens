"use client"

import { useEffect, useState, useRef } from "react"
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
  Loader2
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
  
  // Filter listings for dashboard view (only show items created during this session)
  const sessionListings = listings.filter(l => new Date(l.created_at) > sessionStartTime)
  
  // Stats (based on view)
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

  // Polling effect
  useEffect(() => {
    let interval: NodeJS.Timeout
    let timeout: NodeJS.Timeout

    const checkPollingStatus = async () => {
        // Check if any new listings have appeared since session start
        const response = await api.get("/listings/")
        const newListings = response.data.filter((l: Listing) => new Date(l.created_at) > sessionStartTime)
        
        // If we have listings and polling is active, we might want to stop polling if we assume batch completion
        // But for now, let's just keep polling until timeout or user navigates away
        setListings(response.data)
        setLastUpdated(new Date())
    }

    if (polling) {
      interval = setInterval(checkPollingStatus, 3000) // Poll every 3 seconds

      // Stop polling after 10 minutes to allow for longer scrapes
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
      setPolling(true) // Start polling for results
      // Provide immediate feedback
      // In a real app we'd use a toast here
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

    // Define columns matching legacy output
    const headers = [
      "ID", "Title", "Project Name", "Price", "State", "Area", 
      "Type", "Sq Ft", "Beds", "Baths", "Carpark", "Floor Range", 
      "Phone", "Description", "URL"
    ]
    
    const rows = listings.map(l => [
      l.id,
      `"${(l.listing_title || "").replace(/"/g, '""')}"`,
      `"${(l.project_name || "").replace(/"/g, '""')}"`,
      l.price,
      l.state,
      l.area,
      l.property_type,
      l.sq_ft,
      l.bedrooms,
      l.bathrooms,
      l.carpark,
      l.floor_range,
      `"${(l.phone_number || "").replace(/"/g, '""')}"`,
      `"${(l.description || "").replace(/"/g, '""')}"`,
      l.url
    ])

    const csvContent = [
      headers.join(","),
      ...rows.map(row => row.join(","))
    ].join("\n")

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" })
    const link = document.createElement("a")
    const url = URL.createObjectURL(blob)
    link.setAttribute("href", url)
    link.setAttribute("download", `listings_export_${new Date().toISOString().slice(0,10)}.csv`)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const ListingsTable = ({ data }: { data: Listing[] }) => (
    <div className="overflow-x-auto">
      <table className="w-full text-sm text-left whitespace-nowrap">
        <thead className="text-xs text-gray-500 uppercase bg-gray-50 border-b border-gray-100">
          <tr>
            <th className="px-6 py-4 font-medium">Title / Project</th>
            <th className="px-6 py-4 font-medium">Price</th>
            <th className="px-6 py-4 font-medium">Location</th>
            <th className="px-6 py-4 font-medium">Specs</th>
            <th className="px-6 py-4 font-medium">Type</th>
            <th className="px-6 py-4 font-medium">Contact</th>
            <th className="px-6 py-4 font-medium">Other</th>
            <th className="px-6 py-4 font-medium text-right">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {data.length > 0 ? (
            data.map((listing) => (
              <tr key={listing.id} className="bg-white hover:bg-gray-50/50 transition-colors">
                <td className="px-6 py-4">
                  <div className="font-medium text-gray-900 truncate max-w-[250px]" title={listing.listing_title}>
                    {listing.listing_title || "Untitled Property"}
                  </div>
                  <div className="text-xs text-blue-600 truncate max-w-[250px]">{listing.project_name}</div>
                </td>
                <td className="px-6 py-4 font-semibold text-gray-900">
                  {listing.price ? `RM ${listing.price.toLocaleString()}` : "-"}
                </td>
                <td className="px-6 py-4">
                  <div className="text-gray-900">{listing.area}</div>
                  <div className="text-xs text-gray-500">{listing.state}</div>
                </td>
                <td className="px-6 py-4 text-gray-600">
                  <div className="flex flex-col gap-1 text-xs">
                    <span>{listing.sq_ft ? `${listing.sq_ft} sqft` : "-"}</span>
                    <span className="text-gray-400">
                      {listing.bedrooms || "?"} Beds • {listing.bathrooms || "?"} Baths
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    {listing.property_type || "Unknown"}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-gray-600">
                   {listing.phone_number || "-"}
                </td>
                <td className="px-6 py-4 text-xs text-gray-500">
                   <div>{listing.carpark ? `${listing.carpark} CP` : ""}</div>
                   <div>{listing.floor_range}</div>
                </td>
                <td className="px-6 py-4 text-right">
                  <div className="flex justify-end gap-2">
                    <a 
                      href={listing.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="inline-flex items-center justify-center p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-md transition-colors"
                      title="View Original Listing"
                    >
                      <ExternalLink className="h-4 w-4" />
                    </a>
                    <button
                      onClick={() => handleDelete(listing.id)}
                      className="inline-flex items-center justify-center p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
                      title="Delete Listing"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={8} className="px-6 py-12 text-center text-gray-500">
                <div className="flex flex-col items-center gap-2">
                  <Database className="h-8 w-8 text-gray-300" />
                  <p>No data available yet.</p>
                  <p className="text-xs text-gray-400">Enter URLs above to start building your dataset.</p>
                </div>
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )

  return (
    <div className="flex min-h-screen bg-[var(--background)] text-[var(--foreground)]">
      {/* Sidebar */}
      <aside className="hidden md:flex w-64 flex-col fixed inset-y-0 z-50 bg-white border-r border-gray-200 shadow-lg">
        <div className="p-6 flex items-center gap-2 border-b border-gray-100">
          <Building2 className="h-6 w-6 text-[var(--primary-blue)]" />
          <span className="font-bold text-xl text-[var(--foreground)]">ListingLens</span>
        </div>
        <nav className="flex-1 p-4 space-y-2">
          <button 
            onClick={() => setActiveView('dashboard')}
            className={`w-full px-4 py-2 rounded-lg flex items-center gap-3 font-medium transition-colors ${activeView === 'dashboard' ? 'bg-[var(--light-blue)] text-[var(--primary-blue)]' : 'text-[var(--foreground)] hover:bg-gray-50'}`}
          >
            <LayoutDashboard className="h-5 w-5" />
            Dashboard
          </button>
          <button 
            onClick={() => setActiveView('history')}
            className={`w-full px-4 py-2 rounded-lg flex items-center gap-3 font-medium transition-colors ${activeView === 'history' ? 'bg-[var(--light-blue)] text-[var(--primary-blue)]' : 'text-[var(--foreground)] hover:bg-gray-50'}`}
          >
            <Database className="h-5 w-5" />
            History
          </button>
        </nav>
        <div className="p-6 border-t border-gray-100">
          <div className="bg-[var(--light-blue)] p-4 rounded-lg">
            <h4 className="font-semibold text-[var(--primary-blue)] mb-2 text-sm">Instructions</h4>
            <ol className="text-xs text-[var(--primary-blue)] space-y-2 list-decimal pl-4">
              <li>Paste property URLs</li>
              <li>Click Extract Data</li>
              <li>Wait for AI analysis</li>
              <li>Export to CSV</li>
            </ol>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 md:ml-64">
        <div className="p-8 space-y-8 max-w-[1600px] mx-auto">
          {/* Header */}
          <div className="flex flex-col md:flex-row justify-between md:items-center gap-4">
            <div>
              <h1 className="text-3xl font-bold text-[var(--foreground)]">
                {activeView === 'dashboard' ? 'Property Intelligence' : 'Data History'}
              </h1>
              <p className="text-gray-500 mt-1">
                {activeView === 'dashboard' ? 'AI-powered extraction and analysis dashboard' : 'Archive of all extracted property data'}
              </p>
            </div>
            <div className="flex gap-3">
              {activeView === 'dashboard' && (
                 <Button variant="outline" onClick={() => setSessionStartTime(new Date())} className="gap-2 text-red-600 hover:text-red-700 hover:bg-red-50">
                    <Trash2 className="h-4 w-4" />
                    Clear Dashboard
                 </Button>
              )}
              <Button variant="outline" onClick={() => fetchListings()} className="gap-2">
                <RefreshCw className="h-4 w-4" />
                Refresh
              </Button>
              <Button variant="outline" onClick={handleDownloadCSV} disabled={displayListings.length === 0} className="gap-2">
                <Download className="h-4 w-4" />
                Export CSV
              </Button>
            </div>
          </div>

          {activeView === 'dashboard' ? (
            <>
              {/* Stats Grid */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <Card>
                  <CardContent className="p-6 flex items-center gap-4">
                    <div className="p-3 bg-[var(--light-blue)] rounded-full text-[var(--primary-blue)]">
                      <Home className="h-6 w-6" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-500">Total Properties</p>
                      <h3 className="text-2xl font-bold text-[var(--foreground)]">{totalListings}</h3>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-6 flex items-center gap-4">
                    <div className="p-3 bg-green-100 rounded-full text-green-600">
                      <DollarSign className="h-6 w-6" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-500">Average Price</p>
                      <h3 className="text-2xl font-bold text-[var(--foreground)]">
                        {avgPrice ? `RM ${avgPrice.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : "N/A"}
                      </h3>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-6 flex items-center gap-4">
                    <div className="p-3 bg-purple-100 rounded-full text-purple-600">
                      <MapPin className="h-6 w-6" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-500">States Covered</p>
                      <h3 className="text-2xl font-bold text-[var(--foreground)]">{uniqueStates}</h3>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Extraction Input */}
              <Card className="border-t-4 border-t-[var(--primary-blue)]">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Search className="h-5 w-5 text-[var(--primary-blue)]" />
                    New Extraction
                  </CardTitle>
                  <CardDescription>
                    Paste listing URLs below. Our AI agents will scrape and structure the data automatically.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <textarea
                    className="flex min-h-[120px] w-full rounded-md border border-gray-200 bg-white px-4 py-3 text-sm ring-offset-white placeholder:text-gray-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--primary-blue)] focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 resize-y font-mono"
                    value={urls}
                    onChange={(e) => setUrls(e.target.value)}
                    placeholder="https://www.mudah.my/vi/..."
                    disabled={loading}
                  />
                  <div className="flex justify-between items-center">
                    <div className="text-xs text-gray-500">
                      {polling && (
                        <span className="flex items-center gap-2 text-[var(--primary-blue)] font-medium animate-pulse">
                          <Loader2 className="h-3 w-3 animate-spin" />
                          Processing in background... Data will appear automatically.
                        </span>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <Button 
                        variant="ghost" 
                        onClick={() => setUrls("")} 
                        disabled={!urls || loading}
                        className="text-gray-500 hover:text-red-600"
                      >
                        Clear
                      </Button>
                      <Button 
                        onClick={handleScrape} 
                        disabled={loading || !urls.trim()}
                        className="bg-[var(--primary-blue)] hover:bg-[var(--primary-blue)]/90 text-white min-w-[140px]"
                      >
                        {loading ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Starting...
                          </>
                        ) : (
                          "Start Extraction"
                        )}
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
              
              {/* Recent Data */}
              <Card>
                <CardHeader className="border-b border-gray-100">
                  <div className="flex justify-between items-center">
                    <CardTitle>Current Session Extractions</CardTitle>
                    <span className="text-xs text-gray-400">
                      Last updated: {lastUpdated.toLocaleTimeString()}
                    </span>
                  </div>
                </CardHeader>
                <ListingsTable data={sessionListings} />
                {sessionListings.length === 0 && !polling && (
                   <div className="p-8 text-center text-gray-500">
                      Dashboard cleared. Start a new extraction or view History.
                   </div>
                )}
              </Card>
            </>
          ) : (
            <Card className="min-h-[600px]">
               <CardHeader className="border-b border-gray-100">
                 <div className="flex justify-between items-center">
                   <CardTitle>Full Data History</CardTitle>
                   <Button 
                     variant="outline" 
                     onClick={handleClearHistory} 
                     disabled={listings.length === 0}
                     className="gap-2 text-red-600 hover:text-red-700 hover:bg-red-50 border-red-200"
                   >
                      <Trash2 className="h-4 w-4" />
                      Clear All History
                   </Button>
                 </div>
               </CardHeader>
               <ListingsTable data={listings} />
            </Card>
          )}
        </div>
      </main>
    </div>
  )
}
