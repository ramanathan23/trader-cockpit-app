import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { ScoredSymbol } from '@/domain/dashboard';
import { W, H, PAD, PW, PH } from '@/lib/clusterUtils';
import type { ViewBounds } from '@/lib/clusterUtils';

export function useClusterPanZoom(plotable: ScoredSymbol[], scores: ScoredSymbol[]) {
  const svgRef          = useRef<SVGSVGElement>(null);
  const [viewBounds, setViewBounds] = useState<ViewBounds | null>(null);
  const dragAnchorRef   = useRef<{ svgX: number; svgY: number; bounds: ViewBounds } | null>(null);
  const isDraggingRef   = useRef(false);

  const autoBounds = useMemo<ViewBounds>(() => {
    if (plotable.length === 0) return { x0: 0, x1: 100, y0: 0, y1: 100 };
    const xs     = plotable.map(d => d.total_score);
    const ys     = plotable.map(d => d.comfort_score!);
    const xRange = Math.max(...xs) - Math.min(...xs);
    const yRange = Math.max(...ys) - Math.min(...ys);
    const xpad   = Math.max(4, xRange * 0.12);
    const ypad   = Math.max(4, yRange * 0.12);
    return {
      x0: Math.max(0, Math.min(...xs) - xpad),
      x1: Math.min(100, Math.max(...xs) + xpad),
      y0: Math.max(0, Math.min(...ys) - ypad),
      y1: Math.min(100, Math.max(...ys) + ypad),
    };
  }, [plotable]);

  useEffect(() => { setViewBounds(null); }, [scores]);

  const clientToSvg = useCallback((clientX: number, clientY: number) => {
    const svg = svgRef.current;
    if (!svg) return { x: 0, y: 0 };
    const rect = svg.getBoundingClientRect();
    return { x: ((clientX - rect.left) / rect.width) * W, y: ((clientY - rect.top) / rect.height) * H };
  }, []);

  const handleWheel = useCallback((e: React.WheelEvent<SVGSVGElement>) => {
    e.preventDefault();
    const { x: svgX, y: svgY } = clientToSvg(e.clientX, e.clientY);
    setViewBounds(prev => {
      const cur    = prev ?? autoBounds;
      const focusX = cur.x0 + ((svgX - PAD.left) / PW) * (cur.x1 - cur.x0);
      const focusY = cur.y0 + (1 - (svgY - PAD.top) / PH) * (cur.y1 - cur.y0);
      const factor = e.deltaY > 0 ? 1.15 : 0.87;
      const nx0 = Math.max(0,   focusX - (focusX - cur.x0) * factor);
      const nx1 = Math.min(100, focusX + (cur.x1 - focusX) * factor);
      const ny0 = Math.max(0,   focusY - (focusY - cur.y0) * factor);
      const ny1 = Math.min(100, focusY + (cur.y1 - focusY) * factor);
      if (nx1 - nx0 < 1 || ny1 - ny0 < 1) return prev ?? autoBounds;
      return { x0: nx0, x1: nx1, y0: ny0, y1: ny1 };
    });
  }, [clientToSvg, autoBounds]);

  const handlePointerDown = useCallback((e: React.PointerEvent<SVGSVGElement>) => {
    if (e.button !== 0) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    const { x, y } = clientToSvg(e.clientX, e.clientY);
    dragAnchorRef.current = { svgX: x, svgY: y, bounds: viewBounds ?? autoBounds };
    isDraggingRef.current = false;
  }, [clientToSvg, viewBounds, autoBounds]);

  const handlePointerMove = useCallback((e: React.PointerEvent<SVGSVGElement>) => {
    if (!dragAnchorRef.current) return;
    const { x: svgX, y: svgY } = clientToSvg(e.clientX, e.clientY);
    const dx = svgX - dragAnchorRef.current.svgX;
    const dy = svgY - dragAnchorRef.current.svgY;
    if (!isDraggingRef.current && Math.abs(dx) < 4 && Math.abs(dy) < 4) return;
    isDraggingRef.current = true;
    const b       = dragAnchorRef.current.bounds;
    const dxData  = (dx / PW) * (b.x1 - b.x0);
    const dyData  = -(dy / PH) * (b.y1 - b.y0);
    const nx0 = Math.max(0,   b.x0 - dxData);
    const nx1 = Math.min(100, b.x1 - dxData);
    const ny0 = Math.max(0,   b.y0 - dyData);
    const ny1 = Math.min(100, b.y1 - dyData);
    if (nx0 < nx1 && ny0 < ny1) {
      setViewBounds({ x0: nx0, x1: nx1, y0: ny0, y1: ny1 });
      dragAnchorRef.current = { svgX, svgY, bounds: { x0: nx0, x1: nx1, y0: ny0, y1: ny1 } };
    }
  }, [clientToSvg]);

  const handlePointerUp = useCallback(() => {
    dragAnchorRef.current = null;
    setTimeout(() => { isDraggingRef.current = false; }, 50);
  }, []);

  const cancelDrag = useCallback(() => { dragAnchorRef.current = null; }, []);

  const zoomCenter = useCallback((factor: number) => {
    setViewBounds(prev => {
      const cur = prev ?? autoBounds;
      const cx  = (cur.x0 + cur.x1) / 2;
      const cy  = (cur.y0 + cur.y1) / 2;
      const nx0 = Math.max(0,   cx - (cx - cur.x0) * factor);
      const nx1 = Math.min(100, cx + (cur.x1 - cx) * factor);
      const ny0 = Math.max(0,   cy - (cy - cur.y0) * factor);
      const ny1 = Math.min(100, cy + (cur.y1 - cy) * factor);
      if (nx1 - nx0 < 1 || ny1 - ny0 < 1) return prev ?? autoBounds;
      return { x0: nx0, x1: nx1, y0: ny0, y1: ny1 };
    });
  }, [autoBounds]);

  return { svgRef, viewBounds, setViewBounds, autoBounds, isDraggingRef, cancelDrag, zoomCenter, handleWheel, handlePointerDown, handlePointerMove, handlePointerUp };
}
