from hikaru.generate import add_deprecations_for_release

add_deprecations_for_release("rel_1_26", {('v1', 'Event'): ('v1', 'Event_core')})
