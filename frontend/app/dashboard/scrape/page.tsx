"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { api } from "@/lib/api"

export default function ScrapePage() {
  const [urls, setUrls] = useState("")
  const [loading, setLoading] = useState(false)
  const router = useRouter()

  const handleScrape = async () => {
    setLoading(true)
    try {
      const urlList = urls.split("\n").filter((u) => u.trim() !== "")
      await api.post("/listings/scrape", { urls: urlList })
      // Redirect to dashboard or show success
      router.push("/dashboard")
    } catch (error) {
      console.error("Scraping failed", error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <Card>
        <CardHeader>
          <CardTitle>Add New Listings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
              Property URLs (one per line)
            </label>
            <textarea
              className="flex min-h-[200px] w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm ring-offset-white placeholder:text-slate-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 mt-2"
              value={urls}
              onChange={(e) => setUrls(e.target.value)}
              placeholder="https://example.com/property-1&#10;https://example.com/property-2"
            />
          </div>
          <Button onClick={handleScrape} disabled={loading || !urls.trim()}>
            {loading ? "Starting Scraper..." : "Start Extraction"}
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
