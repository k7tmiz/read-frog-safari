import type { FloatingButtonClickAction } from "@/types/config/floating-button"
import { useAtom } from "jotai"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/base-ui/select"
import { floatingButtonClickActionSchema } from "@/types/config/floating-button"
import { configFieldsAtomMap } from "@/utils/atoms/config"
import { i18n } from "@/utils/i18n"
import { ConfigItem } from "../../../components/config-item"
import { ConfigSection } from "../../../components/config-section"

/**
 * What a click on the button does. The section holds the one row it needs, so the row goes
 * untitled — the heading above it already says what is being set.
 */
export function ClickActionSection() {
  const [floatingButton, setFloatingButton] = useAtom(configFieldsAtomMap.floatingButton)

  // Safari has no sidePanel API and the Safari manifest drops the panel, so the
  // panel action would be a dead click there.
  const supportsSidePanel = import.meta.env.BROWSER !== "safari"

  // Resolved at render (not module scope) so labels follow a runtime UI-language switch.
  const actions = [
    ...(supportsSidePanel
      ? [
          {
            value: "panel" as const,
            label: i18n.t("options.floatingButton.clickAction.panel"),
          },
        ]
      : []),
    {
      value: "translate" as const,
      label: i18n.t("options.floatingButton.clickAction.translate"),
    },
  ] satisfies Array<{ value: FloatingButtonClickAction; label: string }>

  return (
    <ConfigSection
      id="floating-button-click-action"
      title={i18n.t("options.floatingButton.clickAction.title")}
    >
      <ConfigItem description={i18n.t("options.floatingButton.clickAction.description")}>
        <Select
          items={actions}
          value={supportsSidePanel ? floatingButton.clickAction : "translate"}
          onValueChange={(value) => {
            const parsedValue = floatingButtonClickActionSchema.safeParse(value)
            if (!parsedValue.success) return
            void setFloatingButton({ ...floatingButton, clickAction: parsedValue.data })
          }}
        >
          <SelectTrigger size="sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent align="end">
            <SelectGroup>
              {actions.map((action) => (
                <SelectItem key={action.value} value={action.value}>
                  {action.label}
                </SelectItem>
              ))}
            </SelectGroup>
          </SelectContent>
        </Select>
      </ConfigItem>
    </ConfigSection>
  )
}
