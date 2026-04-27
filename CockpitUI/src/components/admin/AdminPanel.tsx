'use client';

import { useState } from 'react';
import type { AdminSection, InitialConfigs } from './adminTypes';
import { AdminNav } from './AdminNav';
import { FullSyncPane } from './FullSyncPane';
import { TokenPane } from './TokenPane';
import { ZerodhaPane } from './ZerodhaPane';
import { ServiceConfigPane } from './ServiceConfigPane';

interface AdminPanelProps {
  initialConfigs?: InitialConfigs | null;
}

/** Root admin panel: sidebar navigation + content pane routing. */
export function AdminPanel({ initialConfigs }: AdminPanelProps) {
  const [section, setSection] = useState<AdminSection>('full-sync');

  const isConfig = (
    section === 'config-datasync' ||
    section === 'config-livefeed'
  );

  const configData =
    section === 'config-datasync' ? initialConfigs?.datasync :
    section === 'config-livefeed' ? initialConfigs?.livefeed : null;

  return (
    <div className="flex min-h-0 flex-1 overflow-hidden">
      <AdminNav section={section} onSection={setSection} />

      <div className="min-w-0 flex-1 overflow-y-auto p-6">
        {/* Always-mounted panes preserve pipeline state + SSE across nav changes. */}
        <div className={section !== 'full-sync' ? 'hidden' : ''}><FullSyncPane /></div>
        <div className={section !== 'zerodha'   ? 'hidden' : ''}><ZerodhaPane /></div>
        <div className={section !== 'token'     ? 'hidden' : ''}><TokenPane /></div>
        {isConfig && (
          <ServiceConfigPane key={section} sectionKey={section} initialConfig={configData} />
        )}
      </div>
    </div>
  );
}
