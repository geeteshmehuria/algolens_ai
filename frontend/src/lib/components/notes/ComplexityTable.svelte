<script lang="ts">
	interface ComplexityRow {
		operation: string;
		time: string;
		space: string;
		note: string;
	}

	interface ComplexityNotesData {
		table: ComplexityRow[];
		how_to_derive: string;
		common_mistakes?: string[];
	}

	let {
		notes
	} = $props<{
		notes: ComplexityNotesData;
	}>();
</script>

<div class="border border-slate-200 bg-white rounded-2xl overflow-hidden shadow-sm flex flex-col gap-4 p-6">
	<div class="flex flex-col gap-1.5">
		<h3 class="text-xs font-bold text-slate-800">Big-O Complexity Analysis</h3>
		<p class="text-[11px] text-slate-400">Strict theoretical bounds expected in technical whiteboard sessions.</p>
	</div>

	<!-- Table -->
	<div class="border border-slate-150 rounded-xl overflow-hidden bg-slate-50/20">
		<table class="w-full text-xs text-left border-collapse">
			<thead>
				<tr class="bg-slate-50 border-b border-slate-200 font-bold text-slate-500 uppercase tracking-wider text-[9px]">
					<th class="px-4 py-3">Operation / Target</th>
					<th class="px-4 py-3">Time</th>
					<th class="px-4 py-3">Space</th>
					<th class="px-4 py-3">Details / Invariant</th>
				</tr>
			</thead>
			<tbody class="divide-y divide-slate-100 font-semibold text-slate-700">
				{#each notes.table as row}
					<tr class="hover:bg-slate-50/40 transition-colors">
						<td class="px-4 py-3 font-bold text-slate-800">{row.operation}</td>
						<td class="px-4 py-3">
							<span class="bg-blue-50 text-blue-700 border border-blue-150 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold">{row.time}</span>
						</td>
						<td class="px-4 py-3">
							<span class="bg-violet-50 text-violet-700 border border-violet-150 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold">{row.space}</span>
						</td>
						<td class="px-4 py-3 text-[11px] text-slate-500 font-medium">{row.note}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>

	<!-- Derivation -->
	<div class="flex flex-col gap-1.5 pt-2">
		<h4 class="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">Mathematical Derivation</h4>
		<p class="text-[11.5px] text-slate-600 leading-relaxed font-medium bg-slate-50 border border-slate-100 p-4 rounded-xl font-mono">{notes.how_to_derive}</p>
	</div>

	<!-- Mistakes -->
	{#if notes.common_mistakes && notes.common_mistakes.length > 0}
		<div class="flex flex-col gap-2 pt-2">
			<h4 class="text-[10px] font-extrabold text-rose-800/80 uppercase tracking-widest">Complexity Traps</h4>
			<ul class="list-disc pl-5 text-[11.5px] text-slate-600 leading-relaxed flex flex-col gap-1.5">
				{#each notes.common_mistakes as mistake}
					<li class="pl-1">
						<strong class="text-rose-600">Mistake:</strong> {mistake}
					</li>
				{/each}
			</ul>
		</div>
	{/if}
</div>
