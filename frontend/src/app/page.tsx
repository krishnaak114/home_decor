'use client';

import { ChangeEvent, useState, useEffect, useCallback } from 'react';

interface SuggestedProduct {
  id: string;
  name: string;
  price: number;
  category: string;
  image_url: string;
  similarity_score?: number;
  metadata?: Record<string, string | number>;
}

interface StyleProfile {
  preferred_styles: string[];
  preferred_rooms: string[];
  preferred_colors: string[];
  liked_product_ids: string[];
  budget_range: [number, number];
  updated_at: string;
}

const USER_ID = 'local_user';
const API = 'http://localhost:8000';
const STYLES = ['Modern', 'Bohemian', 'Scandinavian', 'Industrial', 'Classic', 'Minimalist', 'Rustic', 'Eclectic'];
const ROOMS  = ['Living Room', 'Bedroom', 'Kitchen', 'Dining Room', 'Bathroom', 'Home Office', 'Outdoor'];

interface DesignResult {
  design_id: string;
  style: string;
  colors: string[];
  suggested_products: SuggestedProduct[];
  room_image_url: string;
  original_room_image_url?: string;
  total_value: number;
  analysis?: string;
}

export default function Home() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [filePreview, setFilePreview] = useState<string | null>(null);
  const [wallLength, setWallLength] = useState<string>('');
  const [wallColors, setWallColors] = useState<string>('');
  const [roomDescription, setRoomDescription] = useState<string>('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [designResult, setDesignResult] = useState<DesignResult | null>(null);
  const [previewImageUrl, setPreviewImageUrl] = useState<string | null>(null);
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const [activePreviewId, setActivePreviewId] = useState<string | null>(null);
  const [error, setError] = useState<string>('');
  const [showDetails, setShowDetails] = useState(false);
  const [showCatalogue, setShowCatalogue] = useState(false);
  const [catalogueData, setCatalogueData] = useState<Record<string, SuggestedProduct[]>>({});
  const [isCatalogueLoading, setIsCatalogueLoading] = useState(false);
  
  // Smart Catalogue States
  const [catTopNav, setCatTopNav] = useState('ALL');
  const [selectedProduct, setSelectedProduct] = useState<SuggestedProduct | null>(null);

  // Style Profile
  const [showProfile, setShowProfile] = useState(false);
  const [styleProfile, setStyleProfile] = useState<StyleProfile>({
    preferred_styles: [],
    preferred_rooms: [],
    preferred_colors: [],
    liked_product_ids: [],
    budget_range: [0, 100000],
    updated_at: '',
  });
  const [profileSaved, setProfileSaved] = useState(false);

  // Similar Products
  const [similarProducts, setSimilarProducts] = useState<SuggestedProduct[]>([]);
  const [isSimilarLoading, setIsSimilarLoading] = useState(false);

  const resolveImageUrl = (url?: string) => {
    if (!url) return 'https://via.placeholder.com/400x260?text=No+Image';
    if (url.startsWith('http://') || url.startsWith('https://')) return url;
    return `${API}${url}`;
  };

  // ── Style Profile: load from localStorage on mount ─────────────────────────
  useEffect(() => {
    try {
      const saved = localStorage.getItem(`style_profile_${USER_ID}`);
      if (saved) setStyleProfile(JSON.parse(saved));
    } catch {}
  }, []);

  const saveStyleProfile = useCallback(async (profile: StyleProfile) => {
    const updated = { ...profile, updated_at: new Date().toISOString() };
    setStyleProfile(updated);
    // Persist locally
    localStorage.setItem(`style_profile_${USER_ID}`, JSON.stringify(updated));
    // Sync to backend
    try {
      await fetch(`${API}/api/style-profile/${USER_ID}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updated),
      });
    } catch {}
    setProfileSaved(true);
    setTimeout(() => setProfileSaved(false), 2000);
  }, []);

  const toggleStyleTag = (tag: string, field: 'preferred_styles' | 'preferred_rooms') => {
    const arr = styleProfile[field];
    const next = arr.includes(tag) ? arr.filter(t => t !== tag) : [...arr, tag];
    setStyleProfile(prev => ({ ...prev, [field]: next }));
  };

  const toggleLikeProduct = (productId: string) => {
    const liked = styleProfile.liked_product_ids;
    const next = liked.includes(productId) ? liked.filter(i => i !== productId) : [...liked, productId];
    const updated = { ...styleProfile, liked_product_ids: next };
    saveStyleProfile(updated);
  };

  // ── Similar Products fetch ─────────────────────────────────────────────────
  const fetchSimilarProducts = useCallback(async (productId: string) => {
    setIsSimilarLoading(true);
    setSimilarProducts([]);
    try {
      const res = await fetch(`${API}/api/products/similar/${productId}?limit=6`);
      const data = await res.json();
      setSimilarProducts(data.similar || []);
    } catch {}
    finally { setIsSimilarLoading(false); }
  }, []);

  // Fetch similar whenever selectedProduct changes
  useEffect(() => {
    if (selectedProduct?.id) fetchSimilarProducts(selectedProduct.id);
    else setSimilarProducts([]);
  }, [selectedProduct?.id, fetchSimilarProducts]);

  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const handleFileSelect = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      const reader = new FileReader();
      reader.onloadend = () => setFilePreview(reader.result as string);
      reader.readAsDataURL(file);

      // --- AUTO-ANALYSIS ON UPLOAD ---
      setIsAnalyzing(true);
      setError('');
      try {
        const formData = new FormData();
        formData.append('room_photo', file);
        const response = await fetch(`${API}/api/design/analyze`, {
          method: 'POST',
          body: formData,
        });
        if (response.ok) {
          const data = await response.json();
          if (data.colors) setWallColors(data.colors);
          if (data.description) setRoomDescription(data.description);
          setShowDetails(true); // Automatically expand the details section
        }
      } catch (err) {
        console.error('Auto-analysis failed:', err);
      } finally {
        setIsAnalyzing(false);
      }
    }
  };

  const fetchCatalogue = async () => {
    setIsCatalogueLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/catalogue');
      if (!response.ok) throw new Error('Failed to fetch catalogue');
      const data = await response.json();
      setCatalogueData(data.categories || {});
      setShowCatalogue(true);
    } catch (err) {
      setError('Failed to load catalogue');
      console.error(err);
    } finally {
      setIsCatalogueLoading(false);
    }
  };

  const handleGenerateDesign = async () => {
    if (!selectedFile) {
      setError('Please select a room photo');
      return;
    }

    setIsGenerating(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('room_photo', selectedFile);
      if (wallLength) formData.append('wall_length', wallLength);
      if (wallColors) formData.append('wall_colors', wallColors);
      if (roomDescription) formData.append('room_description', roomDescription);

      const response = await fetch('http://localhost:8000/api/design/generate', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error('Failed to generate design');
      const result = await response.json();
      setDesignResult(result);
    } catch (err) {
      setError('Failed to generate design. Make sure the backend is running.');
      console.error(err);
    } finally {
      setIsGenerating(false);
    }
  };

  const handlePreviewProduct = async (productId: string) => {
    if (!selectedFile) return;

    setIsPreviewLoading(true);
    setActivePreviewId(productId);
    setError('');

    try {
      const formData = new FormData();
      formData.append('room_image', selectedFile);
      formData.append('product_id', productId);
      if (wallLength) formData.append('wall_length', wallLength);

      const response = await fetch('http://localhost:8000/api/design/preview', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error('Failed to generate preview');
      const result = await response.json();

      if (result.error) throw new Error(result.error);

      setPreviewImageUrl(result.preview_url);
    } catch (err: any) {
      setError(err.message || 'Failed to generate preview');
      console.error(err);
    } finally {
      setIsPreviewLoading(false);
    }
  };

  const resetForm = () => {
    setSelectedFile(null);
    setFilePreview(null);
    setWallLength('');
    setWallColors('');
    setRoomDescription('');
    setDesignResult(null);
    setPreviewImageUrl(null);
    setActivePreviewId(null);
    setError('');
    setShowDetails(false);
  };

  return (
    <div className="min-h-screen">
      {/* ── Header ── */}
      <header className="fixed top-0 left-0 right-0 z-50 glass-card-elevated" style={{ borderRadius: 0, borderTop: 'none', borderLeft: 'none', borderRight: 'none' }}>
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #7c5cfc, #a78bfa)' }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                <polyline points="9 22 9 12 15 12 15 22" />
              </svg>
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight" style={{ color: 'var(--foreground)' }}>Home Decor AI</h1>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Powered by Gemini Vision</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <button 
              onClick={fetchCatalogue}
              disabled={isCatalogueLoading}
              className="hidden md:flex items-center gap-2 px-4 py-1.5 rounded-full border border-[var(--border)] hover:border-[var(--accent)] transition-all bg-[var(--surface-elevated)]"
            >
              {isCatalogueLoading ? (
                <div className="w-3 h-3 border-2 border-[var(--accent)] border-t-transparent rounded-full animate-spin" />
              ) : (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)" strokeWidth="2">
                  <path d="M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z" />
                </svg>
              )}
              <span className="text-xs font-bold uppercase tracking-wider">Catalogue</span>
            </button>
            <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full border border-[var(--border-accent)] bg-[var(--accent-glow)]">
              <div className="w-2 h-2 rounded-full bg-[var(--accent)] animate-pulse" />
              <span className="text-xs font-bold" style={{ color: 'var(--accent)' }}>10 CREDITS</span>
            </div>
            <button
              onClick={() => setShowProfile(true)}
              className="hidden md:flex items-center gap-2 px-4 py-1.5 rounded-full border border-[var(--border)] hover:border-[var(--accent)] transition-all bg-[var(--surface-elevated)] relative"
              title="Style Profile"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)" strokeWidth="2"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>
              <span className="text-xs font-bold uppercase tracking-wider">Style Profile</span>
              {styleProfile.preferred_styles.length > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-[var(--accent)] text-white text-[9px] flex items-center justify-center font-bold">
                  {styleProfile.preferred_styles.length}
                </span>
              )}
            </button>
            {designResult && (
              <button onClick={resetForm} className="btn-ghost text-sm">
                + New Design
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 pt-32 pb-10">
        {!designResult ? (
          /* ━━━━━━━━━━ UPLOAD VIEW ━━━━━━━━━━ */
          <div className="max-w-2xl mx-auto fade-in-up">
            <div className="text-center mb-10">
              <h2 className="text-4xl font-extrabold tracking-tight gradient-text mb-3">
                Transform Your Space
              </h2>
              <p className="text-lg" style={{ color: 'var(--text-muted)' }}>
                Upload a room photo and let AI recommend the perfect decor
              </p>
            </div>

            <div className="glass-card-elevated p-8 space-y-6">
              {/* Dropzone */}
              <div>
                <label className="block text-sm font-semibold mb-3" style={{ color: 'var(--text-secondary)' }}>
                  Room Photo
                </label>
                <div className={`dropzone p-8 text-center ${selectedFile ? 'active' : ''} relative`}>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleFileSelect}
                    className="hidden"
                    id="file-input"
                  />
                  <label htmlFor="file-input" className="cursor-pointer block">
                    {filePreview ? (
                      <div className="space-y-3">
                        <img
                          src={filePreview}
                          alt="Room preview"
                          className="max-h-48 mx-auto rounded-lg object-contain"
                        />
                        <div className="flex items-center justify-center gap-2">
                          {isAnalyzing && <div className="w-3 h-3 border-2 border-[var(--accent)] border-t-transparent rounded-full animate-spin" />}
                          <p className="text-sm font-semibold" style={{ color: isAnalyzing ? 'var(--text-muted)' : 'var(--accent)' }}>
                            {isAnalyzing ? 'AI is scanning your room...' : selectedFile?.name}
                          </p>
                        </div>
                        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Click to change</p>
                      </div>
                    ) : (
                      <div className="py-6">
                        <div className="w-16 h-16 mx-auto mb-4 rounded-2xl flex items-center justify-center" style={{ background: 'rgba(124, 92, 252, 0.1)' }}>
                          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#7c5cfc" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                            <circle cx="8.5" cy="8.5" r="1.5" />
                            <polyline points="21 15 16 10 5 21" />
                          </svg>
                        </div>
                        <p className="font-semibold" style={{ color: 'var(--text-secondary)' }}>
                          Drop your room photo here
                        </p>
                        <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
                          or click to browse  &middot;  PNG, JPG up to 10MB
                        </p>
                      </div>
                    )}
                  </label>
                </div>
              </div>

              {/* Room Details */}
              <div className="pt-2">
                <div className="flex items-center justify-between mb-3">
                  <button
                    onClick={() => setShowDetails(!showDetails)}
                    className="flex items-center gap-2 text-sm font-semibold transition-colors"
                    style={{ color: 'var(--text-muted)' }}
                  >
                    <svg
                      width="12" height="12" viewBox="0 0 12 12" fill="currentColor"
                      className={`transition-transform duration-200 ${showDetails ? 'rotate-90' : ''}`}
                    >
                      <path d="M4 2l4 4-4 4" />
                    </svg>
                    Room Configuration
                  </button>
                  {isAnalyzing && <span className="text-[10px] uppercase tracking-widest text-[var(--accent)] font-bold animate-pulse">AI Auto-Filling...</span>}
                </div>
                
                {showDetails && (
                  <div className="space-y-4 fade-in-up">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1.5">
                        <label className="text-[10px] uppercase tracking-widest font-bold ml-1" style={{ color: 'var(--text-muted)' }}>Wall Length (M)</label>
                        <input
                          type="number"
                          step="0.1"
                          value={wallLength}
                          onChange={(e) => setWallLength(e.target.value)}
                          placeholder="Optional"
                          className="w-full px-4 py-3 rounded-xl text-sm font-medium focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
                          style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--foreground)' }}
                        />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-[10px] uppercase tracking-widest font-bold ml-1" style={{ color: 'var(--text-muted)' }}>Detected Colors</label>
                        <input
                          type="text"
                          value={wallColors}
                          onChange={(e) => setWallColors(e.target.value)}
                          placeholder="AI Analyzing..."
                          className="w-full px-4 py-3 rounded-xl text-sm font-medium focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
                          style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--foreground)' }}
                        />
                      </div>
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-[10px] uppercase tracking-widest font-bold ml-1" style={{ color: 'var(--text-muted)' }}>Room Description</label>
                      <textarea
                        value={roomDescription}
                        onChange={(e) => setRoomDescription(e.target.value)}
                        placeholder="AI Analyzing room style..."
                        rows={3}
                        className="w-full px-4 py-3 rounded-xl text-sm font-medium focus:outline-none focus:ring-2 focus:ring-[var(--accent)] resize-none"
                        style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--foreground)' }}
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Error */}
              {error && (
                <div className="rounded-xl p-4 text-sm font-medium" style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', color: '#fca5a5' }}>
                  {error}
                </div>
              )}

              {/* Generate Button */}
              <button
                onClick={handleGenerateDesign}
                disabled={isGenerating || !selectedFile}
                className="btn-accent w-full text-center text-lg"
              >
                {isGenerating ? (
                  <span className="flex items-center justify-center gap-3">
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Analyzing Room...
                  </span>
                ) : (
                  'Generate Design'
                )}
              </button>
            </div>
          </div>
        ) : (
          /* ━━━━━━━━━━ RESULTS VIEW ━━━━━━━━━━ */
          <div className="space-y-8 fade-in-up">
            {/* Hero Section */}
            <div className="glass-card-elevated p-8">
              {/* Style Header */}
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-widest mb-2" style={{ color: 'var(--accent)' }}>
                    AI Design Analysis
                  </p>
                  <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight" style={{ color: 'var(--foreground)' }}>
                    {designResult.style}
                  </h2>
                  {designResult.analysis && (
                    <p className="mt-2 text-sm leading-relaxed max-w-2xl" style={{ color: 'var(--text-muted)' }}>
                      {designResult.analysis}
                    </p>
                  )}
                </div>
              </div>

              {/* Stats Row */}
              <div className="grid grid-cols-3 gap-4 mb-8">
                <div className="stat-pill">
                  <p className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: 'var(--text-muted)' }}>
                    Palette
                  </p>
                  <div className="flex gap-1.5 mt-1">
                    {designResult.colors.map((color, idx) => (
                      <div key={idx} className="color-swatch" style={{ backgroundColor: color }} title={color} />
                    ))}
                  </div>
                </div>
                <div className="stat-pill">
                  <p className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: 'var(--text-muted)' }}>
                    Design Value
                  </p>
                  <p className="text-2xl font-bold" style={{ color: 'var(--success)' }}>
                    ₹{designResult.total_value.toLocaleString()}
                  </p>
                </div>
                <div className="stat-pill">
                  <p className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: 'var(--text-muted)' }}>
                    Products
                  </p>
                  <p className="text-2xl font-bold" style={{ color: 'var(--accent)' }}>
                    {designResult.suggested_products.length}
                  </p>
                </div>
              </div>

              {/* Room Viewer */}
              <div className="room-viewer" style={{ minHeight: '500px' }}>
                <img
                  src={previewImageUrl || resolveImageUrl(designResult.room_image_url)}
                  alt="Your room with AI-placed decor"
                  onError={(e) => {
                    (e.currentTarget as HTMLImageElement).src = 'https://via.placeholder.com/800x500?text=Room+Photo';
                  }}
                />

                {/* Loading overlay */}
                {isPreviewLoading && (
                  <div className="absolute inset-0 flex items-center justify-center" style={{ background: 'rgba(10, 10, 15, 0.7)', backdropFilter: 'blur(4px)' }}>
                    <div className="text-center">
                      <div className="relative w-12 h-12 mx-auto mb-3">
                        <div className="w-12 h-12 border-3 rounded-full animate-spin" style={{ borderColor: 'var(--border)', borderTopColor: 'var(--accent)' }} />
                      </div>
                      <p className="text-sm font-semibold" style={{ color: 'var(--text-secondary)' }}>
                        AI is compositing...
                      </p>
                    </div>
                  </div>
                )}

                {/* Clear preview badge */}
                {previewImageUrl && !isPreviewLoading && (
                  <button
                    onClick={() => { setPreviewImageUrl(null); setActivePreviewId(null); }}
                    className="absolute bottom-4 right-4 btn-ghost text-xs flex items-center gap-1.5"
                    style={{ background: 'rgba(10, 10, 15, 0.8)', backdropFilter: 'blur(8px)' }}
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <line x1="18" y1="6" x2="6" y2="18" />
                      <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                    Clear Preview
                  </button>
                )}
              </div>
            </div>

            {/* Error */}
            {error && (
              <div className="rounded-xl p-4 text-sm font-medium" style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', color: '#fca5a5' }}>
                {error}
              </div>
            )}

            {/* Products Grid */}
            <div>
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="text-xl font-bold" style={{ color: 'var(--foreground)' }}>
                    Recommended Products
                  </h3>
                  <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
                    Click &quot;Preview&quot; to see any product placed in your room
                  </p>
                </div>
              </div>

              <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 stagger">
                {designResult.suggested_products.map((product) => {
                  const isActive = activePreviewId === product.id && previewImageUrl;
                  return (
                    <div
                      key={product.id}
                      className="product-card"
                      style={isActive ? { borderColor: 'var(--accent)', boxShadow: '0 0 0 1px var(--accent), 0 8px 32px rgba(124, 92, 252, 0.2)' } : {}}
                    >
                      <div className="relative overflow-hidden" style={{ background: 'var(--surface-elevated)' }}>
                        <img
                          src={resolveImageUrl(product.image_url)}
                          alt={product.name}
                          className="w-full h-44 object-contain p-3 transition-transform duration-300 hover:scale-105"
                          onError={(e) => {
                            (e.currentTarget as HTMLImageElement).src = 'https://via.placeholder.com/300x200?text=' + encodeURIComponent(product.name);
                          }}
                        />
                        {isActive && (
                          <div className="absolute top-2 right-2 w-6 h-6 rounded-full flex items-center justify-center" style={{ background: 'var(--accent)' }}>
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3">
                              <polyline points="20 6 9 17 4 12" />
                            </svg>
                          </div>
                        )}
                      </div>
                      <div className="p-4">
                        <p className="font-bold text-sm truncate" style={{ color: 'var(--foreground)' }} title={product.name}>
                          {product.name}
                        </p>
                        <p className="text-xs mt-0.5 truncate" style={{ color: 'var(--text-muted)' }}>
                          {product.category}
                        </p>
                        {product.metadata?.size && (
                          <p className="text-xs mt-1.5" style={{ color: 'var(--text-muted)' }}>
                            {String(product.metadata.size)}
                          </p>
                        )}
                        <div className="flex items-center justify-between mt-3">
                          <p className="text-lg font-bold" style={{ color: 'var(--success)' }}>
                            ₹{product.price?.toLocaleString()}
                          </p>
                        </div>
                        <button
                          onClick={() => handlePreviewProduct(product.id)}
                          disabled={isPreviewLoading}
                          className={`w-full mt-3 py-2.5 rounded-xl text-sm font-bold transition-all ${
                            isActive
                              ? 'text-white'
                              : 'hover:border-[var(--accent)] hover:text-[var(--accent)]'
                          }`}
                          style={
                            isActive
                              ? { background: 'linear-gradient(135deg, #7c5cfc, #a78bfa)', color: 'white' }
                              : { background: 'transparent', border: '1px solid var(--border)', color: 'var(--text-secondary)' }
                          }
                        >
                          {isPreviewLoading && activePreviewId === product.id ? (
                            <span className="flex items-center justify-center gap-2">
                              <div className="w-3.5 h-3.5 border-2 border-current/30 border-t-current rounded-full animate-spin" />
                              Placing...
                            </span>
                          ) : isActive ? (
                            'Viewing'
                          ) : (
                            'Preview in Room'
                          )}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </main>

      {/* ── Footer ── */}
      <footer className="mt-auto py-8 text-center" style={{ borderTop: '1px solid var(--border)' }}>
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
          &copy; 2026 Home Decor AI &middot; Powered by Gemini 2.0 Flash &middot; Built by Krishna Agrawal
        </p>
      </footer>
      {/* ── Smart Catalogue Modal (Dark Theme & Dynamic) ── */}
      {showCatalogue && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md animate-in fade-in duration-300">
          <div className="w-full h-full md:w-[95%] md:h-[95%] bg-[var(--background)] border border-[var(--border)] md:rounded-2xl overflow-hidden flex flex-col shadow-2xl text-[var(--foreground)]">
            
            {/* Top Bar Navigation */}
            <div className="bg-[var(--surface-elevated)] px-6 py-4 flex items-center border-b border-[var(--border)] sticky top-0 z-10">
              <div className="text-lg font-black tracking-tighter text-[var(--accent)] mr-8 whitespace-nowrap flex-shrink-0">
                MASTER CATALOGUE
              </div>
              
              <div className="flex-1 overflow-x-auto no-scrollbar flex items-center space-x-5 px-2">
                <button 
                  onClick={() => { setCatTopNav('ALL'); setSelectedProduct(null); }}
                  className={`text-[10px] tracking-widest font-bold uppercase transition-all flex-shrink-0 pb-1 border-b-2 ${catTopNav === 'ALL' ? 'text-[var(--accent)] border-[var(--accent)]' : 'text-[var(--text-muted)] border-transparent hover:text-[var(--foreground)]'}`}
                >
                  ALL ITEMS
                </button>
                {Object.keys(catalogueData).sort().map(nav => (
                  <button 
                    key={nav} 
                    onClick={() => { setCatTopNav(nav); setSelectedProduct(null); }}
                    className={`text-[10px] tracking-widest font-bold uppercase transition-all flex-shrink-0 pb-1 border-b-2 ${catTopNav === nav ? 'text-[var(--accent)] border-[var(--accent)]' : 'text-[var(--text-muted)] border-transparent hover:text-[var(--foreground)]'}`}
                  >
                    {nav}
                  </button>
                ))}
              </div>

              <div className="ml-4 flex-shrink-0">
                <button onClick={() => setShowCatalogue(false)} className="w-8 h-8 rounded-full flex items-center justify-center hover:bg-white/10 text-[var(--text-muted)] hover:text-white transition-all">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M18 6 6 18M6 6l12 12"/></svg>
                </button>
              </div>
            </div>

            {/* Main Content Area */}
            <div className="flex-1 flex overflow-hidden">
              
              {selectedProduct ? (
                /* --- Product Detail View --- */
                <div className="flex-1 overflow-y-auto p-6 md:p-12 flex flex-col md:flex-row gap-12 bg-[var(--background)]">
                  {/* Left: Big Image */}
                  <div className="w-full md:w-1/2 flex flex-col">
                    <button 
                      onClick={() => setSelectedProduct(null)} 
                      className="mb-6 flex items-center text-sm font-bold text-[var(--text-muted)] hover:text-[var(--accent)] transition-colors w-fit"
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="mr-2"><path d="m15 18-6-6 6-6"/></svg>
                      Back to {catTopNav}
                    </button>
                    <div className="w-full aspect-square bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-8 flex items-center justify-center">
                      <img 
                        src={resolveImageUrl(selectedProduct.image_url)} 
                        alt={selectedProduct.name}
                        className="w-full h-full object-contain"
                      />
                    </div>
                  </div>
                  
                  {/* Right: Details */}
                  <div className="w-full md:w-1/2 flex flex-col justify-center">
                    <p className="text-[var(--accent)] text-xs font-bold tracking-widest uppercase mb-2">
                      {selectedProduct.category}
                    </p>
                    <h2 className="text-3xl md:text-5xl font-black mb-6 leading-tight">
                      {selectedProduct.name}
                    </h2>
                    
                    <div className="flex items-baseline gap-4 mb-8">
                      <span className="text-3xl font-black text-[var(--success)]">
                        ₹{selectedProduct.price?.toLocaleString()}
                      </span>
                    </div>

                    <div className="space-y-6 border-t border-[var(--border)] pt-8">
                      {selectedProduct.metadata && Object.entries(selectedProduct.metadata)
                        .filter(([key, val]) => {
                          const ignoredKeys = ['id', 'name', 'price', 'image_url', 'category', 'productname', 'targetprice'];
                          return !ignoredKeys.includes(key.toLowerCase()) && val && String(val).trim() !== '';
                        })
                        .map(([key, val]) => (
                          <div key={key}>
                            <h4 className="text-[var(--text-muted)] text-[10px] font-bold tracking-widest uppercase mb-1">
                              {key.charAt(0).toUpperCase() + key.slice(1).replace(/([A-Z])/g, ' $1').trim()}
                            </h4>
                            <p className="text-lg leading-relaxed text-[var(--text-secondary)]">{String(val)}</p>
                          </div>
                        ))
                      }
                    </div>
                    
                    {/* Action Buttons */}
                    <div className="mt-10 flex flex-wrap gap-3">
                      <button
                        onClick={() => toggleLikeProduct(selectedProduct.id)}
                        className={`flex items-center gap-2 py-3 px-6 rounded-xl font-bold text-sm transition-all border ${
                          styleProfile.liked_product_ids.includes(selectedProduct.id)
                            ? 'bg-pink-500/20 border-pink-500 text-pink-400'
                            : 'bg-transparent border-[var(--border)] text-[var(--text-muted)] hover:border-pink-500 hover:text-pink-400'
                        }`}
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill={styleProfile.liked_product_ids.includes(selectedProduct.id) ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
                        {styleProfile.liked_product_ids.includes(selectedProduct.id) ? 'Liked' : 'Like'}
                      </button>
                      <button
                        onClick={() => { setShowCatalogue(false); }}
                        className="flex items-center gap-2 bg-[var(--accent)] hover:bg-[#9074ff] text-white py-3 px-6 rounded-xl font-bold text-sm transition-colors"
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>
                        Use in Room Design
                      </button>
                    </div>

                    {/* Similar Products */}
                    <div className="mt-10 border-t border-[var(--border)] pt-8">
                      <h3 className="text-xs font-bold tracking-widest uppercase text-[var(--text-muted)] mb-4">Similar Products</h3>
                      {isSimilarLoading ? (
                        <div className="flex gap-3">
                          {[...Array(4)].map((_, i) => <div key={i} className="w-20 h-20 rounded-xl bg-[var(--surface)] animate-pulse" />)}
                        </div>
                      ) : similarProducts.length > 0 ? (
                        <div className="flex gap-3 overflow-x-auto pb-2 no-scrollbar">
                          {similarProducts.map(sp => (
                            <button
                              key={sp.id}
                              onClick={() => setSelectedProduct(sp)}
                              className="flex-shrink-0 w-24 group text-left"
                            >
                              <div className="w-24 h-24 rounded-xl bg-[var(--surface)] border border-[var(--border)] group-hover:border-[var(--accent)] overflow-hidden flex items-center justify-center p-2 transition-all">
                                <img src={resolveImageUrl(sp.image_url)} alt={sp.name} className="w-full h-full object-contain" />
                              </div>
                              <p className="text-[10px] text-[var(--text-muted)] mt-1 truncate">{sp.name}</p>
                              <p className="text-[10px] font-bold text-[var(--success)]">₹{sp.price?.toLocaleString()}</p>
                            </button>
                          ))}
                        </div>
                      ) : (
                        <p className="text-xs text-[var(--text-muted)]">No similar products found.</p>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                /* --- Product Grid View --- */
                <div className="flex-1 overflow-y-auto p-6 md:p-8 bg-[var(--background)]">
                  {Object.entries(catalogueData).length > 0 ? (
                    <div className="grid grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 gap-6">
                      {Object.entries(catalogueData)
                        .filter(([cat]) => catTopNav === 'ALL' || cat === catTopNav)
                        .flatMap(([_, items]) => items)
                        .map((item, idx) => (
                        <div 
                          key={`${item.id}-${idx}`} 
                          onClick={() => setSelectedProduct(item)}
                          className="group cursor-pointer bg-[var(--surface)] border border-[var(--border)] hover:border-[var(--accent)] rounded-xl overflow-hidden transition-all duration-300 hover:shadow-[0_8px_30px_rgb(0,0,0,0.5)]"
                        >
                          <div className="aspect-square bg-black/40 relative overflow-hidden flex items-center justify-center p-6">
                            <img 
                              src={resolveImageUrl(item.image_url)} 
                              alt={item.name}
                              className="w-full h-full object-contain transition-transform duration-700 group-hover:scale-110"
                            />
                            <div className="absolute inset-0 bg-black/0 group-hover:bg-[var(--accent)]/10 transition-colors duration-300" />
                          </div>
                          <div className="p-4 border-t border-[var(--border)] bg-[var(--surface-elevated)]">
                            <p className="text-[10px] font-bold text-[var(--accent)] uppercase tracking-widest mb-1">{item.category}</p>
                            <h4 className="text-sm font-bold text-[var(--foreground)] leading-snug mb-3 h-10 overflow-hidden line-clamp-2" title={item.name}>{item.name}</h4>
                            <div className="flex items-center justify-between">
                              <span className="text-lg font-black text-[var(--success)]">₹{item.price?.toLocaleString()}</span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="h-full flex flex-col items-center justify-center text-center py-20">
                      <p className="text-[var(--text-muted)]">Loading premium collection...</p>
                    </div>
                  )}
                </div>
              )}

            </div>
          </div>
        </div>
      )}

      {/* ── Style Profile Modal ── */}
      {showProfile && (
        <div className="fixed inset-0 z-[60] flex items-end md:items-center justify-center bg-black/80 backdrop-blur-md">
          <div className="w-full md:max-w-lg bg-[var(--surface-elevated)] border border-[var(--border)] md:rounded-2xl rounded-t-2xl p-8 max-h-[90vh] overflow-y-auto shadow-2xl">
            <div className="flex items-center justify-between mb-8">
              <div>
                <h2 className="text-xl font-black text-[var(--foreground)]">Style Profile</h2>
                <p className="text-xs text-[var(--text-muted)] mt-1">Saved across sessions automatically</p>
              </div>
              <button onClick={() => setShowProfile(false)} className="w-8 h-8 rounded-full flex items-center justify-center hover:bg-white/10 text-[var(--text-muted)] transition-all">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M18 6 6 18M6 6l12 12"/></svg>
              </button>
            </div>

            {/* Preferred Styles */}
            <div className="mb-7">
              <h3 className="text-[10px] font-bold tracking-widest uppercase text-[var(--text-muted)] mb-3">Preferred Styles</h3>
              <div className="flex flex-wrap gap-2">
                {STYLES.map(s => (
                  <button key={s} onClick={() => toggleStyleTag(s, 'preferred_styles')}
                    className={`px-3 py-1.5 rounded-full text-xs font-bold border transition-all ${
                      styleProfile.preferred_styles.includes(s)
                        ? 'bg-[var(--accent)] border-[var(--accent)] text-white'
                        : 'bg-transparent border-[var(--border)] text-[var(--text-muted)] hover:border-[var(--accent)]'
                    }`}>{s}</button>
                ))}
              </div>
            </div>

            {/* Preferred Rooms */}
            <div className="mb-7">
              <h3 className="text-[10px] font-bold tracking-widest uppercase text-[var(--text-muted)] mb-3">Preferred Rooms</h3>
              <div className="flex flex-wrap gap-2">
                {ROOMS.map(r => (
                  <button key={r} onClick={() => toggleStyleTag(r, 'preferred_rooms')}
                    className={`px-3 py-1.5 rounded-full text-xs font-bold border transition-all ${
                      styleProfile.preferred_rooms.includes(r)
                        ? 'bg-[var(--accent)] border-[var(--accent)] text-white'
                        : 'bg-transparent border-[var(--border)] text-[var(--text-muted)] hover:border-[var(--accent)]'
                    }`}>{r}</button>
                ))}
              </div>
            </div>

            {/* Budget Range */}
            <div className="mb-8">
              <h3 className="text-[10px] font-bold tracking-widest uppercase text-[var(--text-muted)] mb-3">Budget Range</h3>
              <div className="flex items-center gap-4">
                <span className="text-sm font-bold text-[var(--success)]">₹{styleProfile.budget_range[0].toLocaleString()}</span>
                <input type="range" min={0} max={200000} step={1000}
                  value={styleProfile.budget_range[1]}
                  onChange={e => setStyleProfile(p => ({ ...p, budget_range: [p.budget_range[0], Number(e.target.value)] }))}
                  className="flex-1 accent-[#7c5cfc]"
                />
                <span className="text-sm font-bold text-[var(--success)]">₹{styleProfile.budget_range[1].toLocaleString()}</span>
              </div>
            </div>

            {/* Stats */}
            <div className="bg-[var(--surface)] rounded-xl p-4 mb-6 flex gap-6">
              <div className="text-center">
                <p className="text-2xl font-black text-[var(--accent)]">{styleProfile.preferred_styles.length}</p>
                <p className="text-[10px] text-[var(--text-muted)] mt-0.5">Styles</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-black text-[var(--accent)]">{styleProfile.preferred_rooms.length}</p>
                <p className="text-[10px] text-[var(--text-muted)] mt-0.5">Rooms</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-black text-pink-400">{styleProfile.liked_product_ids.length}</p>
                <p className="text-[10px] text-[var(--text-muted)] mt-0.5">Liked</p>
              </div>
              {styleProfile.updated_at && (
                <div className="text-center ml-auto">
                  <p className="text-[10px] text-[var(--text-muted)]">Last saved</p>
                  <p className="text-[10px] font-bold text-[var(--foreground)]">{new Date(styleProfile.updated_at).toLocaleDateString()}</p>
                </div>
              )}
            </div>

            <button
              onClick={() => saveStyleProfile(styleProfile)}
              className="w-full py-3.5 bg-[var(--accent)] hover:bg-[#9074ff] text-white rounded-xl font-bold text-sm transition-colors flex items-center justify-center gap-2"
            >
              {profileSaved ? (
                <><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg> Saved!</>
              ) : (
                <><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg> Save Profile</>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
