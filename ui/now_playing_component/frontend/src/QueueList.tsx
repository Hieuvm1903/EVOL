import React, { useState } from "react";
import {
  DndContext, closestCenter, PointerSensor, KeyboardSensor, useSensor, useSensors, DragEndEvent,
} from "@dnd-kit/core";
import {
  arrayMove, SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy, useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { HolderOutlined, DownOutlined, RightOutlined } from "@ant-design/icons";
import type { Track } from "./NowPlaying";

function QueueRow({ id, track, isCurrent, onPlay }: {
  id: string; track: Track; isCurrent: boolean; onPlay: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });
  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };
  return (
    <div ref={setNodeRef} style={style} className={`queue-row${isCurrent ? " queue-row-active" : ""}`}>
      <span className="queue-drag-handle" {...attributes} {...listeners}>
        <HolderOutlined />
      </span>
      {track.thumbnail_url
        ? <img className="queue-thumb" src={track.thumbnail_url} alt="" />
        : <div className="queue-thumb queue-thumb-empty" />}
      <span className="queue-title" onClick={onPlay} title={track.title}>{track.title}</span>
      {isCurrent && <span className="queue-now-badge">▶</span>}
    </div>
  );
}

export default function QueueList({ order, queue, currentTrackIdx, onReorder, onPlay }: {
  order: number[];
  queue: Track[];
  currentTrackIdx: number;
  onReorder: (newOrder: number[]) => void;
  onPlay: (trackIdx: number) => void;
}) {
  const [collapsed, setCollapsed] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldPos = order.findIndex((idx) => String(idx) === active.id);
    const newPos = order.findIndex((idx) => String(idx) === over.id);
    if (oldPos === -1 || newPos === -1) return;
    onReorder(arrayMove(order, oldPos, newPos));
  }

  return (
    <div className="queue-section">
      <div className="queue-section-header" onClick={() => setCollapsed((c) => !c)}>
        <span>Queue · {queue.length} tracks</span>
        {collapsed ? <RightOutlined /> : <DownOutlined />}
      </div>
      <div className={`queue-list-wrapper${collapsed ? " collapsed" : ""}`}>
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={order.map(String)} strategy={verticalListSortingStrategy}>
            <div className="queue-list">
              {order.map((origIdx) => (
                <QueueRow
                  key={origIdx}
                  id={String(origIdx)}
                  track={queue[origIdx]}
                  isCurrent={origIdx === currentTrackIdx}
                  onPlay={() => onPlay(origIdx)}
                />
              ))}
            </div>
          </SortableContext>
        </DndContext>
      </div>
    </div>
  );
}