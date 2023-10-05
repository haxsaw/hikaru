from hikaru.generate import add_deprecations_for_release

add_deprecations_for_release("rel_1_27", {('v1', 'Event'): ('v1', 'Event_core')})
