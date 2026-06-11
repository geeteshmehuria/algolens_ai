<script lang="ts">
	interface ChecklistItem {
		key: string;
		label: string;
	}

	let {
		items = [],
		state = {},
		onToggleCheck,
		onMarkTopicCompleted,
		topicCompleted = false
	} = $props<{
		items: ChecklistItem[];
		state: Record<string, boolean>;
		onToggleCheck: (key: string, checked: boolean) => void;
		onMarkTopicCompleted: () => void;
		topicCompleted: boolean;
	}>();

	let allChecked = $derived(
		items.length > 0 && items.every((item: ChecklistItem) => state[item.key] === true)
	);
</script>

<div class="border border-slate-200 bg-white rounded-2xl p-5 shadow-sm flex flex-col gap-4">
	<div class="flex flex-col gap-0.5">
		<h3 class="text-xs font-bold text-slate-800">Confidence Checklist</h3>
		<p class="text-[10px] text-slate-400">Mark off each milestone as you build full mastery.</p>
	</div>

	<div class="flex flex-col gap-2.5">
		{#each items as item}
			{@const checked = state[item.key] === true}
			<label class="flex items-start gap-3 p-3 border border-slate-100 rounded-xl bg-slate-50/50 hover:bg-slate-50 hover:border-slate-200 transition-all cursor-pointer select-none text-[11px] font-semibold text-slate-700 leading-relaxed {checked ? 'bg-emerald-50/10 border-emerald-100/30 text-slate-500' : ''}">
				<input
					type="checkbox"
					{checked}
					onchange={(e) => onToggleCheck(item.key, e.currentTarget.checked)}
					class="rounded border-slate-300 text-blue-600 focus:ring-blue-500 w-4 h-4 cursor-pointer mt-0.5"
				/>
				<span>{item.label}</span>
			</label>
		{/each}
	</div>

	{#if allChecked && !topicCompleted}
		<div class="bg-emerald-50 border border-emerald-200 rounded-2xl p-4 flex flex-col gap-2.5 mt-2 animate-pulse-once">
			<div class="text-[11px] font-bold text-emerald-800 flex items-center gap-1.5">
				<span>🏆</span> Awesome! You checked all items!
			</div>
			<button
				onclick={onMarkTopicCompleted}
				class="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-[10px] py-2 px-3 rounded-lg shadow transition-all"
			>
				Mark Topic as Completed
			</button>
		</div>
	{/if}
</div>

<style>
	@keyframes -global-pulseOnce {
		0% { transform: scale(1); }
		50% { transform: scale(1.02); }
		100% { transform: scale(1); }
	}
	.animate-pulse-once {
		animation: pulseOnce 0.35s ease-out forwards;
	}
</style>
