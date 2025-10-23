import { Plus } from "lucide-react";
import { Outlet } from "react-router";
import { Button } from "@/components/ui/button";
import ScrollContainer from "@/components/valuecell/scroll/scroll-container";
import StockList from "./components/stock-list";
import StockSearchModal from "./components/stock-search-modal";

export default function HomeLayout() {
  return (
    <div className="flex flex-1 gap-4 overflow-hidden bg-gray-100 py-4 pr-4 pl-2">
      <ScrollContainer className="flex-1">
        <Outlet />
      </ScrollContainer>

      <aside className="mt-20 flex min-w-62 flex-col justify-between rounded-xl bg-white">
        <StockList />

        <StockSearchModal>
          <Button
            variant="secondary"
            className="mx-5 mb-6 font-bold text-sm hover:bg-gray-200"
          >
            <Plus size={16} />
            Add Stocks
          </Button>
        </StockSearchModal>
      </aside>
    </div>
  );
}
